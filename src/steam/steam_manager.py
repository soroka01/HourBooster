"""Steam session lifecycle with durable boost-time accounting."""

import logging
import threading
import queue
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from steam.client import EResult
from .auth import AuthError, SteamAuth, TokenSteamClient

from ..storage import Account, Database

logger = logging.getLogger(__name__)


class SessionStatus:
    IDLE = "idle"
    CONNECTING = "connecting"
    AWAITING_GUARD = "awaiting_guard"
    AWAITING_EMAIL = "awaiting_email"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


LIVE_STATUSES = {
    SessionStatus.CONNECTING,
    SessionStatus.AWAITING_GUARD,
    SessionStatus.AWAITING_EMAIL,
    SessionStatus.ACTIVE,
    SessionStatus.STOPPING,
}


@dataclass
class SessionSnapshot:
    account_id: int
    status: str = SessionStatus.IDLE
    error: str = ""
    guard_type: str = ""
    boost_recorded: bool = False


@dataclass
class _Session:
    account: Account
    status: str = SessionStatus.IDLE
    error: str = ""
    guard_type: str = ""
    client: Optional[TokenSteamClient] = None
    thread: Optional[threading.Thread] = None
    boost_recorded: bool = False

    cancelled: threading.Event = field(default_factory=threading.Event)
    codes: queue.Queue = field(default_factory=queue.Queue)

    def snapshot(self) -> SessionSnapshot:
        return SessionSnapshot(
            account_id=self.account.id,
            status=self.status,
            error=self.error,
            guard_type=self.guard_type,
            boost_recorded=self.boost_recorded,
        )


@dataclass(frozen=True)
class _PendingLogin:
    account_id: int
    guard_type: str


class SteamSessionManager:
    """Owns in-memory Steam clients while SQLite persists only durable statistics."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._sessions: Dict[int, _Session] = {}
        self._pending_by_user: Dict[int, _PendingLogin] = {}
        self._lock = threading.RLock()

    def get_snapshot(self, account_id: int) -> SessionSnapshot:
        with self._lock:
            session = self._sessions.get(int(account_id))
            return session.snapshot() if session else SessionSnapshot(account_id=int(account_id))

    def has_live_session(self, account_id: int) -> bool:
        return self.get_snapshot(account_id).status in LIVE_STATUSES

    def start(self, account: Account, user_id: int) -> SessionSnapshot:
        with self._lock:
            current = self._sessions.get(account.id)
            if current and current.status in LIVE_STATUSES:
                return current.snapshot()

            session = _Session(account=account, status=SessionStatus.CONNECTING)
            self._sessions[account.id] = session
            self._launch(session, int(user_id))
            return session.snapshot()

    def submit_guard_code(self, user_id: int, code: str, account_id: Optional[int] = None) -> Optional[SessionSnapshot]:
        with self._lock:
            pending = self._pending_by_user.get(int(user_id))
            target = account_id if account_id is not None else pending.account_id if pending else None
            session = self._sessions.get(target)
            if session is None or session.status not in (SessionStatus.AWAITING_GUARD, SessionStatus.AWAITING_EMAIL):
                return None
            session.codes.put(code)
            session.status = SessionStatus.CONNECTING
            session.error = ""
            return session.snapshot()

    def cancel_pending(self, user_id: int, account_id: Optional[int] = None) -> Optional[int]:
        with self._lock:
            pending = self._pending_by_user.get(int(user_id))
            target = account_id if account_id is not None else pending.account_id if pending else None
            session = self._sessions.get(target)
            if session is None or session.status not in (SessionStatus.AWAITING_GUARD, SessionStatus.AWAITING_EMAIL, SessionStatus.CONNECTING):
                return None
            if pending and pending.account_id == target:
                self._pending_by_user.pop(int(user_id), None)
            self.stop(target)
            return target

    def stop(self, account_id: int) -> bool:
        with self._lock:
            session = self._sessions.get(int(account_id))
            if session is None or session.status not in LIVE_STATUSES:
                return False
            session.cancelled.set()
            session.status = SessionStatus.STOPPING
            # The owning worker closes gevent sockets in its own thread.
            return True

    def _launch(self, session: _Session, user_id: int) -> None:
        session.thread = threading.Thread(
            target=self._run_worker, args=(session, user_id), daemon=True,
            name="steam-account-{0}".format(session.account.id),
        )
        session.thread.start()

    def shutdown(self) -> None:
        with self._lock:
            threads = []
            for session in self._sessions.values():
                session.cancelled.set()
                if session.thread:
                    threads.append(session.thread)
        for thread in threads:
            thread.join()

    def _run_worker(self, session: _Session, user_id: int) -> None:
        client = None
        auth = SteamAuth()
        try:
            guard_type = auth.begin(session.account.username, session.account.password)
            if session.cancelled.is_set():
                return
            if guard_type:
                self._set_pending(session, user_id, guard_type)
            deadline = time.monotonic() + 300
            token = None
            while not session.cancelled.is_set() and time.monotonic() < deadline:
                try:
                    code = session.codes.get_nowait()
                except queue.Empty:
                    code = None
                if code:
                    try:
                        auth.submit_code(code)
                    except AuthError as error:
                        if error.code not in (65, 88):
                            raise
                        self._set_pending(session, user_id, guard_type)
                        with self._lock:
                            session.error = str(error)
                        continue
                token = auth.poll()
                if token:
                    break
                session.cancelled.wait(auth.interval)
            if session.cancelled.is_set():
                return
            if not token:
                raise AuthError("Время подтверждения входа истекло. Запустите аккаунт заново.")
            with self._lock:
                session.status = SessionStatus.CONNECTING
                session.guard_type = ""
                session.error = ""
                pending = self._pending_by_user.get(user_id)
                if pending and pending.account_id == session.account.id:
                    self._pending_by_user.pop(user_id, None)
            client = TokenSteamClient()
            session.client = client
            result = client.login_token(session.account.username, auth.steam_id, token)
            token = None
            if session.cancelled.is_set():
                return
            if result != EResult.OK:
                raise AuthError("Steam отклонил вход по токену ({0}, код {1}).".format(result.name, int(result)))
            with self._lock:
                if session.cancelled.is_set():
                    return
                client.set_played_games(session.account.games, session.account.custom_game_name)
                self._database.start_boost(session.account.id)
                session.boost_recorded = True
                session.status = SessionStatus.ACTIVE
            logger.info("Steam-сессия %s активна", session.account.id)
            while client.connected and client.logged_on and not session.cancelled.is_set():
                client.sleep(0.2)
        except AuthError as error:
            if not session.cancelled.is_set():
                self._set_error(session, str(error))
        except Exception as error:
            # Do not include HTTP payloads, credentials or tokens in logs/UI.
            logger.error("Ошибка Steam-сессии %s: %s", session.account.id, type(error).__name__)
            if not session.cancelled.is_set():
                self._set_error(session, "Не удалось завершить вход или Steam-сессию. Повторите запуск.")
        finally:
            auth.close()
            if client:
                try:
                    client.disconnect()
                except Exception:
                    logger.warning("Не удалось закрыть Steam-соединение аккаунта %s", session.account.id)
            with self._lock:
                if session.boost_recorded:
                    self._database.stop_boost(session.account.id)
                session.boost_recorded = False
                session.client = None
                session.thread = None
                if session.cancelled.is_set() or session.status == SessionStatus.ACTIVE:
                    session.status = SessionStatus.STOPPED
                    session.guard_type = ""
                pending = self._pending_by_user.get(user_id)
                if pending and pending.account_id == session.account.id:
                    self._pending_by_user.pop(user_id, None)
                while not session.codes.empty():
                    session.codes.get_nowait()

    def _set_pending(self, session: _Session, user_id: int, guard_type: str) -> None:
        with self._lock:
            if session.cancelled.is_set():
                return
            session.status = SessionStatus.AWAITING_EMAIL if guard_type == "email" else SessionStatus.AWAITING_GUARD
            session.guard_type = guard_type
            session.error = ""
            self._pending_by_user[user_id] = _PendingLogin(session.account.id, guard_type)

    def _set_error(self, session: _Session, message: str) -> None:
        with self._lock:
            session.status = SessionStatus.ERROR
            session.error = message
            session.guard_type = ""
