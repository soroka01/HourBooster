"""Steam session lifecycle: automatic reconnects, Steam Guard automation and durable boost-time accounting."""

import hashlib
import logging
import threading
import queue
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from steam.client import EResult
from steam.enums.emsg import EMsg
from .auth import AuthError, SteamAuth, THROTTLE_DELAY, TokenSteamClient, refresh_token_expiry
from .guard import generate_code, seconds_to_next_window, steam_clock

from ..storage import Account, Database

logger = logging.getLogger(__name__)

# Timings are module-level so tests can shrink them.
RECONNECT_FIRST_DELAY = 2.0      # pause before the first retry after a dropped connection
RECONNECT_MAX_DELAY = 60.0
STABLE_AFTER = 30.0              # a connection shorter than this counts as flapping, not as recovery
LOGON_SPACING = 1.5              # minimum gap between logons of all accounts (VPN comes back -> no storm)
OUTAGE_ALERT_AFTER = 90.0        # tell the owner only about outages longer than this
OUTAGE_ALERT_COOLDOWN = 1800.0
AUTH_TIMEOUT = 300.0             # user-started login: how long to wait for a Guard code
AUTO_GUARD_ATTEMPTS = 3
CREDENTIAL_AUTHS_PER_HOUR = 4
TOKEN_MIN_LIFETIME = 600
POLL_FAILURES_BEFORE_RETRY = 20
SHUTDOWN_JOIN_TIMEOUT = 15.0
RESUME_GAMES_INTERVAL = 30.0

TRANSIENT_RESULTS = frozenset({
    EResult.Fail, EResult.NoConnection, EResult.Busy, EResult.Timeout, EResult.ServiceUnavailable,
    EResult.ServiceReadOnly, EResult.TryAnotherCM, EResult.RateLimitExceeded,
    EResult.AccountLoginDeniedThrottle,
})
THROTTLED_RESULTS = frozenset({EResult.RateLimitExceeded, EResult.AccountLoginDeniedThrottle})
FATAL_RESULTS = frozenset({
    EResult.Banned, EResult.AccountNotFound, EResult.AccountDisabled, EResult.AccountLockedDown,
    EResult.AccountLogonDeniedVerifiedEmailRequired, EResult.RestrictedDevice, EResult.RegionLocked,
})
# Another client took the session; logging back in would kick the user out of their own Steam.
KICKED_RESULTS = frozenset({EResult.LoggedInElsewhere, EResult.LogonSessionReplaced})


class SessionStatus:
    IDLE = "idle"
    CONNECTING = "connecting"
    RECONNECTING = "reconnecting"
    AWAITING_GUARD = "awaiting_guard"
    AWAITING_EMAIL = "awaiting_email"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    PAUSED = "paused"


LIVE_STATUSES = {
    SessionStatus.CONNECTING,
    SessionStatus.RECONNECTING,
    SessionStatus.AWAITING_GUARD,
    SessionStatus.AWAITING_EMAIL,
    SessionStatus.ACTIVE,
    SessionStatus.STOPPING,
    SessionStatus.PAUSED,
}

_AWAITING = (SessionStatus.AWAITING_GUARD, SessionStatus.AWAITING_EMAIL)


@dataclass
class SessionSnapshot:
    account_id: int
    status: str = SessionStatus.IDLE
    error: str = ""
    guard_type: str = ""
    boost_recorded: bool = False
    reconnect_attempt: int = 0
    down_since: Optional[float] = None
    retry_at: Optional[float] = None


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
    # Per connection: reset whenever a new Steam client is created.
    was_active: bool = False
    game_confirmed: bool = False
    playing_blocked: bool = False
    blocked_pause: bool = False
    logoff_result: Optional[int] = None
    last_resume_at: float = 0.0
    # Per session: survives reconnects.
    background: bool = False  # started by the bot itself (autostart): nobody is watching the screen
    ever_active: bool = False
    reconnect_attempt: int = 0
    down_since: Optional[float] = None
    retry_at: Optional[float] = None
    outage_alerted: bool = False
    last_outage_alert: Optional[float] = None
    pending_alerted: bool = False
    credential_auths: List[float] = field(default_factory=list)
    codes: queue.Queue = field(default_factory=queue.Queue)  # (code, is_auto)

    @property
    def interactive(self) -> bool:
        """The owner pressed Start and is waiting for the first login (short deadline, hard errors)."""
        return not (self.ever_active or self.background)

    def snapshot(self) -> SessionSnapshot:
        return SessionSnapshot(
            account_id=self.account.id,
            status=self.status,
            error=self.error,
            guard_type=self.guard_type,
            boost_recorded=self.boost_recorded,
            reconnect_attempt=self.reconnect_attempt,
            down_since=self.down_since,
            retry_at=self.retry_at,
        )


@dataclass(frozen=True)
class _PendingLogin:
    account_id: int
    user_id: int
    guard_type: str
    session: "_Session" = field(compare=False, repr=False)


@dataclass(frozen=True)
class _StoredToken:
    fingerprint: str
    token: str = field(repr=False)
    steam_id: int


class _Stop(Exception):
    """The session was cancelled by the user or by shutdown."""


class _Retry(Exception):
    """A temporary failure; try again after a pause of at least ``min_delay`` seconds."""

    def __init__(self, reason: str, min_delay: float = 0.0) -> None:
        super().__init__(reason)
        self.min_delay = min_delay


class _AuthExpired(Exception):
    """Steam dropped the pending login request; ``carried_code`` is a user code worth resubmitting."""

    def __init__(self, carried_code: Optional[str] = None) -> None:
        super().__init__("auth session expired")
        self.carried_code = carried_code


def _duration_text(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds >= 120:
        return "{0} мин".format(seconds // 60)
    return "{0} с".format(seconds)


def _fingerprint(account: Account) -> str:
    material = "{0}\0{1}".format(account.username.lower(), account.password)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class SteamSessionManager:
    """Owns in-memory Steam clients while SQLite persists only durable statistics.

    Each account runs in its own worker thread (gevent clients live in the thread that created them).
    The worker keeps the account online: it reconnects with the refresh token, falls back to a
    password login with an automatic Steam Guard code, and only asks the owner when it must.
    Invariant: nothing blocks on ``threading``/``requests`` while that thread has a connected client.
    """

    def __init__(self, database: Database) -> None:
        self._database = database
        self._sessions: Dict[int, _Session] = {}
        self._pending: Dict[int, _PendingLogin] = {}
        self._tokens: Dict[int, _StoredToken] = {}  # refresh tokens never leave memory
        self._lock = threading.RLock()
        self._logon_lock = threading.Lock()
        self._next_logon_at = 0.0
        self.alerts: queue.Queue = queue.Queue()

    def _notify(self, session: _Session, message: str, kind: str = "warning") -> None:
        if not session.cancelled.is_set():
            self.alerts.put((session.account.id, session.account.title, message, kind))
            logger.warning("Steam-аккаунт %s: %s", session.account.id, message)

    def _playing_state(self, session: _Session, client: TokenSteamClient, message) -> None:
        with self._lock:
            if session.cancelled.is_set() or session.client is not client:
                return
            blocked = bool(message.body.playing_blocked)
            app_id = int(message.body.playing_app)
            session.playing_blocked = blocked
            if session.status == SessionStatus.PAUSED and session.blocked_pause and not blocked and not app_id:
                # The other device left; ask Steam to play our games again (rate-limited).
                session.blocked_pause = False
                self._resume_games(session, client)
                return
            lost_game = session.game_confirmed and not app_id
            if session.was_active and (blocked or lost_game):
                if session.status == SessionStatus.PAUSED:
                    return
                self._end_boost(session)
                session.status = SessionStatus.PAUSED
                session.blocked_pause = blocked
                session.error = ("Steam заблокировал игру в этой сессии: аккаунт играет на другом устройстве."
                                 if blocked else "Steam сообщил о выходе из игры.")
                self._notify(session, session.error + " Учёт буста приостановлен; подключение сохранено.")
            elif not blocked and app_id:
                session.game_confirmed = True
                if session.status == SessionStatus.PAUSED:
                    self._database.start_boost(session.account.id)
                    session.boost_recorded = True
                    session.status = SessionStatus.ACTIVE
                    session.error = ""

    def _resume_games(self, session: _Session, client: TokenSteamClient) -> None:
        now = time.monotonic()
        if now - session.last_resume_at < RESUME_GAMES_INTERVAL:
            return
        session.last_resume_at = now
        client.set_played_games(session.account.games, session.account.custom_game_name)

    def _logged_off(self, session: _Session, client: TokenSteamClient, message) -> None:
        with self._lock:
            if session.client is client:
                session.logoff_result = int(message.body.eresult)

    def get_snapshot(self, account_id: int) -> SessionSnapshot:
        with self._lock:
            session = self._sessions.get(int(account_id))
            return session.snapshot() if session else SessionSnapshot(account_id=int(account_id))

    def has_live_session(self, account_id: int) -> bool:
        return self.get_snapshot(account_id).status in LIVE_STATUSES

    def forget_account(self, account_id: int) -> None:
        """Drop the in-memory refresh token (credentials changed or the account was deleted)."""
        with self._lock:
            self._tokens.pop(int(account_id), None)

    def start(self, account: Account, user_id: int, background: bool = False) -> SessionSnapshot:
        with self._lock:
            current = self._sessions.get(account.id)
            if current and current.status in LIVE_STATUSES:
                return current.snapshot()

            # Starting by hand is the owner's wish to keep it running, also after a restart of the bot.
            self._database.set_autostart(account.id, True)
            session = _Session(account=account, status=SessionStatus.CONNECTING, background=background)
            self._sessions[account.id] = session
            self._launch(session, int(user_id))
            return session.snapshot()

    def autostart(self, user_id: int) -> int:
        """Resume the accounts that were running (and not stopped by hand) when the bot last exited."""
        started = 0
        for account in self._database.list_autostart_accounts():
            if not self.has_live_session(account.id):
                self.start(account, user_id, background=True)
                started += 1
        if started:
            logger.info("Автозапуск аккаунтов после перезапуска: %s", started)
        return started

    def _resolve_target(self, user_id: int, account_id: Optional[int]) -> Optional[int]:
        if account_id is not None:
            return int(account_id)
        for pending in self._pending.values():
            if pending.user_id == int(user_id):
                return pending.account_id
        return None

    def submit_guard_code(self, user_id: int, code: str, account_id: Optional[int] = None) -> Optional[SessionSnapshot]:
        with self._lock:
            session = self._sessions.get(self._resolve_target(user_id, account_id))
            if session is None or session.status not in _AWAITING:
                return None
            session.codes.put((code, False))
            session.status = SessionStatus.CONNECTING
            session.error = ""
            return session.snapshot()

    def cancel_pending(self, user_id: int, account_id: Optional[int] = None) -> Optional[int]:
        with self._lock:
            target = self._resolve_target(user_id, account_id)
            session = self._sessions.get(target)
            if session is None or session.status not in _AWAITING + (
                    SessionStatus.CONNECTING, SessionStatus.RECONNECTING):
                return None
            self.stop(target)
            return target

    def stop(self, account_id: int) -> bool:
        with self._lock:
            self._database.set_autostart(int(account_id), False)
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
        deadline = time.monotonic() + SHUTDOWN_JOIN_TIMEOUT
        for thread in threads:
            thread.join(max(0.0, deadline - time.monotonic()))
        with self._lock:
            self._tokens.clear()

    # ------------------------------------------------------------------ worker

    def _run_worker(self, session: _Session, user_id: int) -> None:
        try:
            self._supervise(session, user_id)
        except _Stop:
            pass
        except AuthError as error:
            self._fail(session, str(error))
        except Exception as error:
            # Do not include HTTP payloads, credentials or tokens in logs/UI.
            logger.error("Ошибка Steam-сессии %s: %s", session.account.id, type(error).__name__)
            self._fail(session, "Не удалось завершить вход или Steam-сессию. Повторите запуск.")
        finally:
            self._finish(session)

    def _supervise(self, session: _Session, user_id: int) -> None:
        strikes = 0   # consecutive failed attempts, or short-lived connections
        delay = 0.0
        while True:
            self._pause(session, delay)
            try:
                client = self._establish(session, user_id)
            except _Retry as retry:
                strikes += 1
                self._attempt_failed(session, str(retry))
                delay = max(self._backoff(strikes), retry.min_delay)
                continue

            connected_at = time.monotonic()
            self._recovered(session)
            reason = None
            try:
                self._hold(session, client)
                reason = session.logoff_result
            finally:
                self._dispose(client)
                with self._lock:
                    self._end_boost(session)
                    session.client = None
            self._check_cancel(session)
            if reason is not None and reason in KICKED_RESULTS:
                raise AuthError(
                    "Steam закрыл сессию: аккаунт вошёл в Steam на другом устройстве или компьютере. "
                    "Автопереподключение отключено, чтобы не вытеснять вас из Steam. "
                    "Запустите аккаунт вручную, когда он освободится."
                )
            strikes = 0 if time.monotonic() - connected_at >= STABLE_AFTER else strikes + 1
            self._connection_lost(session, reason)
            delay = RECONNECT_FIRST_DELAY if strikes == 0 else self._backoff(strikes)

    @staticmethod
    def _backoff(strikes: int) -> float:
        delay = min(RECONNECT_MAX_DELAY, RECONNECT_FIRST_DELAY * 2 ** max(0, strikes - 1))
        return delay + random.uniform(0, delay * 0.25)

    def _check_cancel(self, session: _Session) -> None:
        if session.cancelled.is_set():
            raise _Stop()

    def _pause(self, session: _Session, delay: float) -> None:
        if delay > 0:
            with self._lock:
                session.retry_at = time.time() + delay
            if session.cancelled.wait(delay):
                raise _Stop()
        with self._logon_lock:
            now = time.monotonic()
            start = max(now, self._next_logon_at)
            self._next_logon_at = start + LOGON_SPACING
        if start > now and session.cancelled.wait(start - now):
            raise _Stop()
        with self._lock:
            session.retry_at = None
        self._check_cancel(session)

    def _hold(self, session: _Session, client: TokenSteamClient) -> None:
        while client.connected and client.logged_on and not session.cancelled.is_set():
            client.sleep(0.2)
        if not session.cancelled.is_set():
            # A trailing ClientLoggedOff is parsed in its own greenlet; let it land.
            client.sleep(0.5)

    def _dispose(self, client: Optional[TokenSteamClient]) -> None:
        if client is None:
            return
        for close in (client.disconnect, client.connection.disconnect):
            try:
                close()
            except Exception:
                logger.warning("Не удалось закрыть Steam-соединение")
        try:
            client.sleep(0.05)
        except Exception:
            pass

    def _end_boost(self, session: _Session) -> None:
        with self._lock:
            if session.boost_recorded:
                self._database.stop_boost(session.account.id)
                session.boost_recorded = False

    # --------------------------------------------------------- outage bookkeeping

    def _connection_lost(self, session: _Session, reason: Optional[int]) -> None:
        with self._lock:
            if session.cancelled.is_set():
                return
            session.status = SessionStatus.RECONNECTING
            session.down_since = time.time()
            session.reconnect_attempt = 0
            session.error = "Соединение со Steam потеряно. Переподключаюсь автоматически."
            logger.warning("Steam-аккаунт %s: соединение потеряно%s; переподключение", session.account.id,
                           "" if reason is None else " (Steam: {0})".format(int(reason)))

    def _attempt_failed(self, session: _Session, reason: str) -> None:
        with self._lock:
            if session.cancelled.is_set():
                return
            now = time.time()
            if session.down_since is None:
                session.down_since = now
            session.reconnect_attempt += 1
            session.status = SessionStatus.RECONNECTING
            session.guard_type = ""
            pending = self._pending.get(session.account.id)
            if pending and pending.session is session:
                self._pending.pop(session.account.id, None)
            session.error = "Нет связи со Steam: {0} Повторяю попытки.".format(
                reason if reason.endswith(".") else reason + ".")
            logger.warning("Steam-аккаунт %s: попытка переподключения %s не удалась: %s",
                           session.account.id, session.reconnect_attempt, reason)
            down = now - session.down_since
            cooled = (session.last_outage_alert is None
                      or time.monotonic() - session.last_outage_alert >= OUTAGE_ALERT_COOLDOWN)
            watched = not session.interactive
            if watched and not session.outage_alerted and down >= OUTAGE_ALERT_AFTER and cooled:
                session.outage_alerted = True
                session.last_outage_alert = time.monotonic()
                self._notify(session, "Нет связи со Steam уже {0}. Продолжаю переподключаться автоматически "
                                      "(попытка {1}).".format(_duration_text(down), session.reconnect_attempt))

    def _recovered(self, session: _Session) -> None:
        with self._lock:
            if session.outage_alerted and session.down_since is not None:
                self._notify(session, "Соединение со Steam восстановлено через {0}.".format(
                    _duration_text(time.time() - session.down_since)), "ok")
            session.down_since = None
            session.retry_at = None
            session.reconnect_attempt = 0
            session.outage_alerted = False

    # ------------------------------------------------------------------ connect

    def _establish(self, session: _Session, user_id: int) -> TokenSteamClient:
        """Return a logged-in client that is already playing (or paused because another device plays)."""
        account = session.account
        stored = self._usable_token(account)
        fresh = False
        while True:
            if stored is None:
                try:
                    stored = self._authenticate(session, user_id)
                except AuthError as error:
                    if error.transient:
                        raise _Retry(str(error), error.retry_after) from None
                    raise
                fresh = True
            client, result = self._logon(session, stored)
            if result == EResult.OK:
                break
            if result in FATAL_RESULTS:
                raise AuthError("Steam не пускает этот аккаунт ({0}, код {1}).".format(result.name, int(result)))
            if result in TRANSIENT_RESULTS:
                raise _Retry("Steam временно недоступен ({0}).".format(result.name),
                             THROTTLE_DELAY if result in THROTTLED_RESULTS else 0.0)
            with self._lock:
                self._tokens.pop(account.id, None)
            stored = None
            if fresh:
                raise AuthError("Steam отклонил вход по токену ({0}, код {1}).".format(result.name, int(result)))
            logger.info("Steam-аккаунт %s: токен больше не принимается, вход по паролю", account.id)
        try:
            self._activate(session, client)
        except BaseException:
            self._dispose(client)
            with self._lock:
                session.client = None
            raise
        return client

    def _usable_token(self, account: Account) -> Optional[_StoredToken]:
        with self._lock:
            stored = self._tokens.get(account.id)
            if stored is None:
                return None
            expiry = refresh_token_expiry(stored.token)
            if stored.fingerprint != _fingerprint(account) or (
                    expiry is not None and expiry - time.time() < TOKEN_MIN_LIFETIME):
                self._tokens.pop(account.id, None)
                return None
            return stored

    def _logon(self, session: _Session, stored: _StoredToken) -> Tuple[Optional[TokenSteamClient], EResult]:
        account = session.account
        client = TokenSteamClient()
        client.on(EMsg.ClientPlayingSessionState, lambda message, c=client: self._playing_state(session, c, message))
        client.on(EMsg.ClientLoggedOff, lambda message, c=client: self._logged_off(session, c, message))
        with self._lock:
            self._check_cancel(session)
            session.client = client
            session.logoff_result = None
            session.playing_blocked = False
            session.game_confirmed = False
            session.was_active = False
            session.blocked_pause = False
            session.status = self._busy_status(session)
        try:
            result = client.login_token(account.username, stored.steam_id, stored.token, cancelled=session.cancelled)
        except Exception as error:
            logger.warning("Сбой входа Steam-аккаунта %s: %s", account.id, type(error).__name__)
            self._dispose(client)
            with self._lock:
                session.client = None
            raise _Retry("Сбой соединения со Steam при входе.") from None
        if session.cancelled.is_set() or result != EResult.OK:
            self._dispose(client)
            with self._lock:
                session.client = None
        self._check_cancel(session)
        return client, result

    def _busy_status(self, session: _Session) -> str:
        return SessionStatus.RECONNECTING if session.down_since is not None else SessionStatus.CONNECTING

    def _activate(self, session: _Session, client: TokenSteamClient) -> None:
        with self._lock:
            self._check_cancel(session)
            if session.playing_blocked:
                if session.interactive:
                    raise AuthError("Steam не разрешает запуск: аккаунт уже играет на другом устройстве.")
                # Reconnected (or restarted) while another device plays: stay online and resume when Steam frees it.
                session.blocked_pause = True
                session.was_active = True
                session.ever_active = True
                session.status = SessionStatus.PAUSED
                session.error = "Аккаунт играет на другом устройстве. Учёт буста приостановлен; подключение сохранено."
                self._notify(session, session.error)
                return
            client.set_played_games(session.account.games, session.account.custom_game_name)
            self._database.start_boost(session.account.id)
            session.boost_recorded = True
            session.status = SessionStatus.ACTIVE
            session.error = ""
            session.was_active = True
            session.ever_active = True
        logger.info("Steam-сессия %s активна", session.account.id)

    # ----------------------------------------------------------- authentication

    def _authenticate(self, session: _Session, user_id: int) -> _StoredToken:
        """Sign in with the password (and an automatic or manual Guard code); keeps the refresh token in memory."""
        account = session.account
        interactive = session.interactive
        carried: Optional[str] = None
        for _ in range(4):
            try:
                token, steam_id = self._auth_round(session, user_id, interactive, carried)
            except _AuthExpired as expired:
                if interactive and expired.carried_code is None and not account.shared_secret:
                    raise AuthError("Время подтверждения входа истекло. Запустите аккаунт заново.") from None
                carried = expired.carried_code
                continue
            stored = _StoredToken(_fingerprint(account), token, steam_id)
            with self._lock:
                self._tokens[account.id] = stored
            return stored
        raise AuthError("Запрос подтверждения входа в Steam постоянно истекает. Запустите аккаунт заново.")

    def _spend_credential_auth(self, session: _Session) -> None:
        now = time.monotonic()
        session.credential_auths = [moment for moment in session.credential_auths if now - moment < 3600]
        if len(session.credential_auths) >= CREDENTIAL_AUTHS_PER_HOUR:
            raise AuthError("Слишком частые повторные входы по паролю: Steam, похоже, не принимает токен. "
                            "Проверьте аккаунт и запустите его вручную.")
        session.credential_auths.append(now)

    @staticmethod
    def _auto_code(account: Account, resync: bool = False) -> str:
        return generate_code(account.shared_secret, steam_clock.now(force=resync))

    def _auth_round(self, session: _Session, user_id: int, interactive: bool,
                    carried_code: Optional[str]) -> Tuple[str, int]:
        account = session.account
        auth = SteamAuth()
        while not session.codes.empty():
            session.codes.get_nowait()  # a code typed for an earlier request is useless here
        try:
            guard_type = auth.begin(account.username, account.password)
            self._check_cancel(session)
            # Only logins Steam actually accepted count; an outage must not use up the budget.
            self._spend_credential_auth(session)
            auto_budget = AUTO_GUARD_ATTEMPTS if guard_type == "mobile" and account.shared_secret else 0
            next_auto_at: Optional[float] = None
            deadline = time.monotonic() + AUTH_TIMEOUT if interactive else None
            poll_failures = 0
            if carried_code:
                session.codes.put((carried_code, False))
            elif auto_budget:
                auto_budget -= 1
                session.codes.put((self._auto_code(account), True))
            elif guard_type:
                self._set_pending(session, user_id, guard_type, alert=not interactive)

            while True:
                self._check_cancel(session)
                if deadline is not None and time.monotonic() >= deadline:
                    raise AuthError("Время подтверждения входа истекло. Запустите аккаунт заново.")
                try:
                    code, is_auto = session.codes.get_nowait()
                except queue.Empty:
                    code, is_auto = None, False
                if code:
                    try:
                        auth.submit_code(code)
                    except AuthError as error:
                        if error.transient:
                            session.codes.put((code, is_auto))
                            session.cancelled.wait(auth.interval)
                            continue
                        if error.code == 27:
                            raise _AuthExpired(None if is_auto else code) from None
                        if not error.code:
                            # Steam wants an in-app confirmation, not a typed code.
                            self._set_pending(session, user_id, guard_type, str(error))
                            continue
                        if error.code not in (65, 88):
                            raise
                        if not is_auto:
                            self._set_pending(session, user_id, guard_type, str(error))
                        elif auto_budget:
                            auto_budget -= 1
                            next_auto_at = time.time() + seconds_to_next_window(steam_clock.now())
                        else:
                            self._set_pending(
                                session, user_id, guard_type,
                                "Автоматический код Steam Guard не принят. Проверьте shared_secret и время "
                                "на компьютере; введите код вручную.", alert=not interactive)
                        continue
                if next_auto_at is not None and time.time() >= next_auto_at:
                    next_auto_at = None
                    session.codes.put((self._auto_code(account, resync=True), True))
                    continue
                try:
                    token = auth.poll()
                    poll_failures = 0
                except AuthError as error:
                    if error.code == 27:
                        raise _AuthExpired(None) from None
                    if not error.transient:
                        raise
                    poll_failures += 1
                    if poll_failures > POLL_FAILURES_BEFORE_RETRY:
                        raise
                    token = None
                if token:
                    break
                session.cancelled.wait(auth.interval)

            with self._lock:
                self._check_cancel(session)
                session.guard_type = ""
                session.error = ""
                session.pending_alerted = False
                session.status = self._busy_status(session)
                pending = self._pending.get(account.id)
                if pending and pending.session is session:
                    self._pending.pop(account.id, None)
            return token, auth.steam_id
        finally:
            auth.close()

    def _set_pending(self, session: _Session, user_id: int, guard_type: str, message: str = "",
                     alert: bool = False) -> None:
        with self._lock:
            if session.cancelled.is_set():
                return
            session.status = SessionStatus.AWAITING_EMAIL if guard_type == "email" else SessionStatus.AWAITING_GUARD
            session.guard_type = guard_type
            session.error = message
            self._pending[session.account.id] = _PendingLogin(session.account.id, user_id, guard_type, session)
            if alert and not session.pending_alerted:
                session.pending_alerted = True
                hints = {
                    "mobile": "нужен код Steam Guard (или подтверждение в приложении Steam)",
                    "email": "нужен код из письма Steam",
                }
                self._notify(session, "Для входа {0}. Откройте аккаунт в боте.".format(
                    hints.get(guard_type, "подтвердите вход в приложении Steam или по ссылке из письма")))

    # ------------------------------------------------------------------ endings

    def _fail(self, session: _Session, message: str) -> None:
        with self._lock:
            if session.cancelled.is_set():
                return
            session.status = SessionStatus.ERROR
            session.error = message
            session.guard_type = ""
            # A hard failure (bad password, kicked, banned) must not repeat on every restart.
            self._database.set_autostart(session.account.id, False)
            if session.ever_active or session.background:
                self._notify(session, message)

    def _finish(self, session: _Session) -> None:
        with self._lock:
            self._end_boost(session)
            session.client = None
            session.thread = None
            session.retry_at = None
            if session.cancelled.is_set() or session.status != SessionStatus.ERROR:
                session.status = SessionStatus.STOPPED
                session.guard_type = ""
            pending = self._pending.get(session.account.id)
            if pending and pending.session is session:
                self._pending.pop(session.account.id, None)
            while not session.codes.empty():
                session.codes.get_nowait()
