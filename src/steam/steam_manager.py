"""Steam session lifecycle with durable boost-time accounting."""

import logging
import threading
from dataclasses import dataclass
from typing import Dict, Optional

from steam.client import EResult, SteamClient

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
    client: Optional[SteamClient] = None
    thread: Optional[threading.Thread] = None
    boost_recorded: bool = False

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

    def submit_guard_code(self, user_id: int, code: str) -> Optional[SessionSnapshot]:
        with self._lock:
            pending = self._pending_by_user.pop(int(user_id), None)
            if pending is None:
                return None

            session = self._sessions.get(pending.account_id)
            if session is None:
                return None

            session.status = SessionStatus.CONNECTING
            session.error = ""
            session.guard_type = ""
            if pending.guard_type == "mobile":
                self._launch(session, int(user_id), two_factor_code=code)
            else:
                self._launch(session, int(user_id), email_code=code)
            return session.snapshot()

    def cancel_pending(self, user_id: int) -> Optional[int]:
        with self._lock:
            pending = self._pending_by_user.pop(int(user_id), None)
            if pending is None:
                return None
            session = self._sessions.get(pending.account_id)
            if session:
                session.status = SessionStatus.STOPPED
                session.guard_type = ""
                session.error = "Ввод кода отменён пользователем."
                client = session.client
            else:
                client = None

        if client:
            try:
                client.logout()
            except Exception:
                logger.debug("Не удалось завершить ожидающий Steam-клиент", exc_info=True)
        return pending.account_id

    def stop(self, account_id: int) -> bool:
        with self._lock:
            session = self._sessions.get(int(account_id))
            if session is None or session.status not in LIVE_STATUSES:
                return False

            for user_id, pending in list(self._pending_by_user.items()):
                if pending.account_id == session.account.id:
                    del self._pending_by_user[user_id]

            session.status = SessionStatus.STOPPING
            client = session.client
            thread = session.thread

        try:
            if client:
                client.logout()
            if thread and thread.is_alive():
                thread.join(timeout=5)
            return True
        except Exception:
            logger.exception("Ошибка при остановке Steam-клиента %s", account_id)
            with self._lock:
                session = self._sessions.get(int(account_id))
                if session:
                    session.status = SessionStatus.ERROR
                    session.error = "Не удалось остановить Steam-клиент."
            return False

    def _launch(
        self,
        session: _Session,
        user_id: int,
        two_factor_code: Optional[str] = None,
        email_code: Optional[str] = None,
    ) -> None:
        thread = threading.Thread(
            target=self._run_worker,
            args=(session.account.id, int(user_id), two_factor_code, email_code),
            daemon=True,
            name="steam-account-{0}".format(session.account.id),
        )
        session.thread = thread
        thread.start()

    def _run_worker(
        self,
        account_id: int,
        user_id: int,
        two_factor_code: Optional[str],
        email_code: Optional[str],
    ) -> None:
        session: Optional[_Session] = None
        try:
            with self._lock:
                session = self._sessions.get(int(account_id))
                if session is None:
                    return
                account = session.account

            client = SteamClient()
            with self._lock:
                if self._sessions.get(int(account_id)) is not session:
                    return
                session.client = client

            login_kwargs = {"username": account.username, "password": account.password}
            if two_factor_code:
                login_kwargs["two_factor_code"] = two_factor_code
            elif email_code:
                login_kwargs["auth_code"] = email_code

            logger.info("Подключение Steam для аккаунта %s", account.id)
            result = client.login(**login_kwargs)
            result_code = getattr(result, "value", None)

            if result == EResult.OK:
                self._database.start_boost(account.id)
                with self._lock:
                    session.status = SessionStatus.ACTIVE
                    session.error = ""
                    session.guard_type = ""
                    session.boost_recorded = True
                    self._pending_by_user.pop(int(user_id), None)

                client.games_played(list(account.games))
                logger.info("Steam-сессия %s активна", account.id)
                client.run_forever()
                return

            if result_code == 85:
                self._set_pending(session, int(user_id), "mobile")
                return
            if result_code == 63:
                self._set_pending(session, int(user_id), "email")
                return

            self._set_error(session, "Steam отклонил вход (код {0}).".format(result_code))
        except Exception as error:
            logger.exception("Ошибка Steam-сессии %s", account_id)
            if session:
                self._set_error(session, "Ошибка Steam: {0}".format(str(error)[:120]))
        finally:
            if session is not None:
                with self._lock:
                    boost_recorded = session.boost_recorded
                    state_before_cleanup = session.status
                    session.client = None

                if boost_recorded:
                    self._database.stop_boost(session.account.id)

                with self._lock:
                    if state_before_cleanup in (SessionStatus.ACTIVE, SessionStatus.STOPPING):
                        session.status = SessionStatus.STOPPED
                        session.boost_recorded = False
                    if session.thread is threading.current_thread():
                        session.thread = None

    def _set_pending(self, session: _Session, user_id: int, guard_type: str) -> None:
        with self._lock:
            session.status = (
                SessionStatus.AWAITING_GUARD if guard_type == "mobile" else SessionStatus.AWAITING_EMAIL
            )
            session.guard_type = guard_type
            session.error = ""
            self._pending_by_user[int(user_id)] = _PendingLogin(
                account_id=session.account.id,
                guard_type=guard_type,
            )

    def _set_error(self, session: _Session, message: str) -> None:
        with self._lock:
            session.status = SessionStatus.ERROR
            session.error = message
            session.guard_type = ""
