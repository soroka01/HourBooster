"""Supervisor behaviour with a fake Steam: drops, rejected tokens, automatic Guard codes, kicks."""

import base64
import dataclasses
import os
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

from steam.enums import EResult
from steam.enums.emsg import EMsg

from src.i18n import t
from src.steam import steam_manager
from src.steam.auth import AuthError
from src.steam.guard import generate_code
from src.steam.steam_manager import SessionStatus, SteamSessionManager
from src.storage import Database

NOW = 1700000000.0
USER = 1


class World:
    """Everything the fake Steam does, scripted per test."""

    def __init__(self):
        self.guard_type = None
        self.valid_codes = set()
        self.begin_calls = 0
        self.begin_errors = []
        self.submitted = []
        self.logon_results = []
        self.logon_tokens = []
        self.logon_hook = None
        self.clients = []
        self.tokens_issued = 0
        self.approved = False
        self.expire_submits = 0


def make_fakes(world):
    class FakeAuth:
        def __init__(self):
            self.interval = 0.01
            self.steam_id = 76561198000000001
            self.accepted = False

        def begin(self, username, password):
            world.begin_calls += 1
            if world.begin_errors:
                raise world.begin_errors.pop(0)
            self.accepted = world.guard_type not in ("mobile", "email", "confirmation")
            return world.guard_type

        def submit_code(self, code):
            world.submitted.append(code)
            if world.guard_type == "confirmation":
                raise AuthError(t("steam.auth.confirm_in_app"))
            if world.expire_submits:
                world.expire_submits -= 1
                raise AuthError("Запрос входа истёк.", 27)
            if code not in world.valid_codes:
                raise AuthError("Неверный код Steam Guard.", 88)
            self.accepted = True

        def poll(self):
            if world.guard_type == "confirmation" and world.approved:
                self.accepted = True
            if not self.accepted:
                return None
            world.tokens_issued += 1
            return "token-{0}".format(world.tokens_issued)

        def close(self):
            pass

    class FakeClient:
        def __init__(self):
            world.clients.append(self)
            self.connected = False
            self.logged_on = False
            self.handlers = {}
            self.played = None
            self.disconnects = 0
            self.connection = types.SimpleNamespace(disconnect=lambda: None)

        def on(self, emsg, handler):
            self.handlers[emsg] = handler

        def login_token(self, username, steam_id, token, cancelled=None):
            world.logon_tokens.append(token)
            result = world.logon_results.pop(0) if world.logon_results else EResult.OK
            if result == EResult.OK:
                self.connected = self.logged_on = True
                if world.logon_hook:
                    world.logon_hook(self)
            return result

        def set_played_games(self, app_ids, custom_name=""):
            self.played = list(app_ids)

        def sleep(self, seconds):
            time.sleep(min(seconds, 0.005))

        def disconnect(self):
            self.disconnects += 1
            self.connected = self.logged_on = False

        def drop(self):
            self.connected = self.logged_on = False

        def say(self, emsg, **body):
            self.handlers[emsg](types.SimpleNamespace(body=types.SimpleNamespace(**body)))

    return FakeAuth, FakeClient


class ManagerCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.database = Database(Path(temp.name) / "test.sqlite3")
        self.addCleanup(self.database.close)
        self.world = World()
        auth_class, client_class = make_fakes(self.world)
        patches = [
            mock.patch.object(steam_manager, "SteamAuth", auth_class),
            mock.patch.object(steam_manager, "TokenSteamClient", client_class),
            mock.patch.object(steam_manager.steam_clock, "now", lambda force=False: NOW),
            mock.patch.object(steam_manager, "seconds_to_next_window", lambda moment: 0.01),
            mock.patch.object(steam_manager, "RECONNECT_FIRST_DELAY", 0.01),
            mock.patch.object(steam_manager, "RECONNECT_MAX_DELAY", 0.05),
            mock.patch.object(steam_manager, "THROTTLE_DELAY", 0.1),
            mock.patch.object(steam_manager, "STABLE_AFTER", 0.0),
            mock.patch.object(steam_manager, "LOGON_SPACING", 0.0),
            mock.patch.object(steam_manager, "OUTAGE_ALERT_AFTER", 0.05),
            mock.patch.object(steam_manager, "AUTH_TIMEOUT", 0.3),
            mock.patch.object(steam_manager, "SHUTDOWN_JOIN_TIMEOUT", 2.0),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.manager = SteamSessionManager(self.database)
        self.addCleanup(self.manager.shutdown)
        self.secret = base64.b64encode(os.urandom(20)).decode()
        self.account = self.database.create_account("Main", "login", "pw", [730, 570])

    def with_secret(self):
        self.account = self.database.update_account(self.account.id, "shared_secret", self.secret)
        self.world.valid_codes = {generate_code(self.secret, NOW)}

    def start(self):
        self.manager.start(self.account, USER)

    def status(self):
        return self.manager.get_snapshot(self.account.id).status

    def wait_for(self, predicate, what, timeout=5.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.005)
        self.fail("не дождались: {0} (статус {1})".format(what, self.manager.get_snapshot(self.account.id)))

    def wait_status(self, status, timeout=5.0):
        self.wait_for(lambda: self.status() == status, "статус " + status, timeout)

    def wait_clients(self, count):
        self.wait_for(lambda: len(self.world.clients) >= count, "{0}-й клиент Steam".format(count))

    def drain_alerts(self):
        alerts = []
        while not self.manager.alerts.empty():
            alerts.append(self.manager.alerts.get_nowait())
        return alerts

    def stop_and_wait(self):
        self.manager.stop(self.account.id)
        self.wait_status(SessionStatus.STOPPED)


class ReconnectTests(ManagerCase):
    def test_drop_reconnects_with_the_token_and_no_new_login(self):
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        first = self.world.clients[0]
        self.assertEqual(first.played, [730, 570])

        first.drop()
        self.wait_clients(2)
        self.wait_status(SessionStatus.ACTIVE)

        self.assertEqual(self.world.begin_calls, 1)
        self.assertEqual(self.world.logon_tokens, ["token-1", "token-1"])
        self.assertEqual(self.world.clients[1].played, [730, 570])
        self.assertGreaterEqual(first.disconnects, 1)
        self.assertEqual(self.drain_alerts(), [])
        stats = self.database.get_account_stats(self.account.id)
        self.assertEqual(stats.completed_sessions, 1)
        self.assertTrue(stats.is_active)

        self.stop_and_wait()
        stats = self.database.get_account_stats(self.account.id)
        self.assertEqual(stats.completed_sessions, 2)
        self.assertFalse(stats.is_active)

    def test_token_survives_stop_and_start_but_not_a_password_change(self):
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.stop_and_wait()

        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.assertEqual(self.world.begin_calls, 1)
        self.stop_and_wait()

        self.account = dataclasses.replace(self.account, password="changed")
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.assertEqual(self.world.begin_calls, 2)
        self.stop_and_wait()

        self.manager.forget_account(self.account.id)
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.assertEqual(self.world.begin_calls, 3)

    def test_transient_results_retry_with_the_same_token(self):
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.world.logon_results = [EResult.Timeout, EResult.ServiceUnavailable]
        self.world.clients[0].drop()
        self.wait_clients(4)
        self.wait_status(SessionStatus.ACTIVE)
        self.assertEqual(self.world.begin_calls, 1)
        self.assertEqual(set(self.world.logon_tokens), {"token-1"})

    def test_rate_limit_waits_long_and_never_falls_back_to_password(self):
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.world.logon_results = [EResult.RateLimitExceeded]
        started = time.monotonic()
        self.world.clients[0].drop()
        self.wait_clients(3)
        self.wait_status(SessionStatus.ACTIVE)
        self.assertGreaterEqual(time.monotonic() - started, 0.1)
        self.assertEqual(self.world.begin_calls, 1)

    def test_stop_during_backoff_is_immediate(self):
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.world.logon_results = [EResult.RateLimitExceeded] * 5
        self.world.clients[0].drop()
        self.wait_status(SessionStatus.RECONNECTING)
        self.wait_clients(2)
        started = time.monotonic()
        self.stop_and_wait()
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertFalse(self.database.get_account_stats(self.account.id).is_active)

    def test_outage_alert_is_sent_once_and_recovery_follows(self):
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.world.logon_results = [EResult.Timeout] * 12
        self.world.clients[0].drop()
        self.wait_for(lambda: self.manager.alerts.qsize() >= 2, "оповещения об обрыве и восстановлении")
        self.wait_status(SessionStatus.ACTIVE)
        alerts = self.drain_alerts()
        self.assertEqual([item[3] for item in alerts], ["warning", "ok"])
        self.assertTrue(alerts[0][2].startswith(t("steam.alert.outage", duration="@", attempt=0).split("@")[0]))
        self.assertTrue(alerts[1][2].startswith(t("steam.alert.restored", duration="@").split("@")[0]))

    def test_network_errors_during_password_login_do_not_exhaust_the_budget(self):
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.world.logon_results = [EResult.AccessDenied]
        self.world.begin_errors = [AuthError("нет сети", transient=True) for _ in range(8)]
        self.world.clients[0].drop()
        self.wait_for(lambda: self.world.begin_calls >= 10, "10 попыток входа")
        self.wait_status(SessionStatus.ACTIVE)
        # 1 initial login + 8 network failures + 1 success; the hourly password-login budget is untouched.
        self.assertEqual(self.world.begin_calls, 10)


class GuardTests(ManagerCase):
    def test_rejected_token_triggers_password_login_with_automatic_code(self):
        self.world.guard_type = "mobile"
        self.with_secret()
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.assertEqual(self.world.submitted, [generate_code(self.secret, NOW)])

        self.world.logon_results = [EResult.AccessDenied]
        self.world.clients[0].drop()
        self.wait_clients(3)
        self.wait_status(SessionStatus.ACTIVE)

        self.assertEqual(self.world.begin_calls, 2)
        self.assertEqual(self.world.submitted, [generate_code(self.secret, NOW)] * 2)
        self.assertEqual(self.world.logon_tokens, ["token-1", "token-1", "token-2"])
        self.assertEqual(self.drain_alerts(), [])

    def test_rejected_automatic_code_falls_back_to_manual_entry(self):
        self.world.guard_type = "mobile"
        self.account = self.database.update_account(self.account.id, "shared_secret", self.secret)
        self.start()
        self.wait_status(SessionStatus.AWAITING_GUARD)
        self.assertEqual(len(self.world.submitted), 3)
        self.assertEqual(self.manager.get_snapshot(self.account.id).error, t("steam.session.auto_code_rejected"))
        self.assertEqual(self.drain_alerts(), [])

        self.world.valid_codes = {"ABCDE"}
        snapshot = self.manager.submit_guard_code(USER, "ABCDE", self.account.id)
        self.assertEqual(snapshot.status, SessionStatus.CONNECTING)
        self.wait_status(SessionStatus.ACTIVE)
        self.assertEqual(self.world.submitted[-1], "ABCDE")

    def test_background_manual_code_alerts_once_and_waits_without_deadline(self):
        self.world.guard_type = "mobile"
        self.world.valid_codes = {"GOOD"}
        self.start()
        self.wait_status(SessionStatus.AWAITING_GUARD)
        self.manager.submit_guard_code(USER, "GOOD", self.account.id)
        self.wait_status(SessionStatus.ACTIVE)

        self.world.logon_results = [EResult.AccessDenied]
        self.world.clients[0].drop()
        self.wait_status(SessionStatus.AWAITING_GUARD)
        alerts = self.drain_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertIn(t("steam.hint.mobile"), alerts[0][2])

        time.sleep(0.6)  # twice the interactive deadline
        self.assertEqual(self.status(), SessionStatus.AWAITING_GUARD)
        self.assertEqual(self.drain_alerts(), [])

        self.manager.submit_guard_code(USER, "GOOD", self.account.id)
        self.wait_status(SessionStatus.ACTIVE)

    def test_expired_request_resubmits_the_typed_code(self):
        self.world.guard_type = "mobile"
        self.world.valid_codes = {"GOOD"}
        self.world.expire_submits = 1
        self.start()
        self.wait_status(SessionStatus.AWAITING_GUARD)
        self.manager.submit_guard_code(USER, "GOOD", self.account.id)
        self.wait_status(SessionStatus.ACTIVE)
        self.assertEqual(self.world.begin_calls, 2)
        self.assertEqual(self.world.submitted, ["GOOD", "GOOD"])

    def test_expired_request_does_not_fail_an_automatic_login(self):
        self.world.guard_type = "mobile"
        self.with_secret()
        self.world.expire_submits = 1
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.assertEqual(self.world.begin_calls, 2)

    def test_typing_a_code_while_steam_wants_an_app_confirmation_is_not_fatal(self):
        self.world.guard_type = "confirmation"
        self.start()
        self.wait_status(SessionStatus.AWAITING_GUARD)
        self.manager.submit_guard_code(USER, "123", self.account.id)
        self.wait_for(lambda: self.world.submitted == ["123"] and self.status() == SessionStatus.AWAITING_GUARD,
                      "возврат к ожиданию подтверждения")
        self.assertEqual(self.manager.get_snapshot(self.account.id).error, t("steam.auth.confirm_in_app"))
        self.world.approved = True
        self.wait_status(SessionStatus.ACTIVE)

    def test_interactive_start_times_out_without_a_code(self):
        self.world.guard_type = "mobile"
        self.start()
        self.wait_status(SessionStatus.ERROR)
        self.assertEqual(self.manager.get_snapshot(self.account.id).error, t("steam.session.login_expired"))

    def test_password_rejection_is_fatal_and_not_retried(self):
        self.world.begin_errors = [AuthError("Steam не принял логин или пароль (код 5).", 5)]
        self.start()
        self.wait_status(SessionStatus.ERROR)
        time.sleep(0.1)
        self.assertEqual(self.world.begin_calls, 1)
        self.assertEqual(len(self.world.clients), 0)


class KickAndPauseTests(ManagerCase):
    def test_logged_in_elsewhere_stops_auto_reconnect(self):
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        client = self.world.clients[0]
        client.say(EMsg.ClientLoggedOff, eresult=int(EResult.LoggedInElsewhere))
        client.drop()
        self.wait_status(SessionStatus.ERROR)
        time.sleep(0.1)
        self.assertEqual(len(self.world.clients), 1)
        alerts = self.drain_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0][2], t("steam.session.kicked"))
        self.assertFalse(self.database.get_account_stats(self.account.id).is_active)

    def test_first_start_while_another_device_plays_is_an_error(self):
        self.world.logon_hook = lambda client: client.say(
            EMsg.ClientPlayingSessionState, playing_blocked=True, playing_app=0)
        self.start()
        self.wait_status(SessionStatus.ERROR)
        self.assertEqual(self.manager.get_snapshot(self.account.id).error, t("steam.session.playing_elsewhere"))
        self.assertEqual(len(self.world.clients), 1)

    def test_reconnect_while_another_device_plays_pauses_then_resumes(self):
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.drain_alerts()

        self.world.logon_hook = lambda client: client.say(
            EMsg.ClientPlayingSessionState, playing_blocked=True, playing_app=0)
        self.world.clients[0].drop()
        self.wait_status(SessionStatus.PAUSED)
        second = self.world.clients[1]
        self.assertIsNone(second.played)
        self.assertFalse(self.database.get_account_stats(self.account.id).is_active)

        second.say(EMsg.ClientPlayingSessionState, playing_blocked=False, playing_app=0)
        self.assertEqual(second.played, [730, 570])
        second.say(EMsg.ClientPlayingSessionState, playing_blocked=False, playing_app=730)
        self.assertEqual(self.status(), SessionStatus.ACTIVE)
        self.assertTrue(self.database.get_account_stats(self.account.id).is_active)

    def test_events_of_a_replaced_client_are_ignored(self):
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        first = self.world.clients[0]
        first.drop()
        self.wait_clients(2)
        self.wait_status(SessionStatus.ACTIVE)
        first.say(EMsg.ClientPlayingSessionState, playing_blocked=True, playing_app=0)
        self.assertEqual(self.status(), SessionStatus.ACTIVE)

    def test_shutdown_ends_active_sessions_and_closes_accounting(self):
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.manager.shutdown()
        self.assertFalse(self.database.get_account_stats(self.account.id).is_active)
        self.assertEqual(self.status(), SessionStatus.STOPPED)


class AutostartTests(ManagerCase):
    def remembered(self, account_id=None):
        return self.database.get_account(account_id or self.account.id).autostart

    def test_start_is_remembered_and_a_manual_stop_forgets_it(self):
        self.assertFalse(self.remembered())
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.assertTrue(self.remembered())
        self.stop_and_wait()
        self.assertFalse(self.remembered())

    def test_restart_of_the_bot_resumes_only_the_accounts_that_were_running(self):
        other = self.database.create_account("Other", "other", "pw", [440])
        self.start()
        self.wait_status(SessionStatus.ACTIVE)
        self.manager.shutdown()
        self.assertTrue(self.remembered())
        self.assertFalse(self.remembered(other.id))

        restarted = SteamSessionManager(self.database)
        self.addCleanup(restarted.shutdown)
        self.assertEqual(restarted.autostart(USER), 1)
        self.wait_for(lambda: restarted.get_snapshot(self.account.id).status == SessionStatus.ACTIVE,
                      "автозапуск аккаунта после перезапуска")
        self.assertEqual(restarted.get_snapshot(other.id).status, SessionStatus.IDLE)
        self.assertEqual(restarted.autostart(USER), 0)

    def test_hard_failure_does_not_repeat_on_every_restart(self):
        self.world.begin_errors = [AuthError("Steam не принял логин или пароль (код 5).", 5)]
        self.start()
        self.wait_status(SessionStatus.ERROR)
        self.assertFalse(self.remembered())

    def test_unattended_start_waits_for_a_code_and_tells_the_owner(self):
        self.world.guard_type = "mobile"
        self.world.valid_codes = {"GOOD"}
        self.database.set_autostart(self.account.id, True)
        self.assertEqual(self.manager.autostart(USER), 1)
        self.wait_status(SessionStatus.AWAITING_GUARD)
        alerts = self.drain_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertIn(t("steam.hint.mobile"), alerts[0][2])

        time.sleep(0.6)  # twice the deadline of a start the owner is watching
        self.assertEqual(self.status(), SessionStatus.AWAITING_GUARD)
        self.manager.submit_guard_code(USER, "GOOD", self.account.id)
        self.wait_status(SessionStatus.ACTIVE)
        self.assertTrue(self.remembered())

    def test_unattended_start_with_a_secret_needs_nobody(self):
        self.world.guard_type = "mobile"
        self.with_secret()
        self.database.set_autostart(self.account.id, True)
        self.manager.autostart(USER)
        self.wait_status(SessionStatus.ACTIVE)
        self.assertEqual(self.drain_alerts(), [])

    def test_unattended_start_while_another_device_plays_pauses_instead_of_failing(self):
        self.world.logon_hook = lambda client: client.say(
            EMsg.ClientPlayingSessionState, playing_blocked=True, playing_app=0)
        self.database.set_autostart(self.account.id, True)
        self.manager.autostart(USER)
        self.wait_status(SessionStatus.PAUSED)
        self.assertTrue(self.remembered())

    def test_unattended_outage_alerts_even_before_the_first_login(self):
        self.world.logon_results = [EResult.Timeout] * 12
        self.database.set_autostart(self.account.id, True)
        self.manager.autostart(USER)
        self.wait_for(lambda: self.manager.alerts.qsize() >= 2, "оповещения об обрыве и восстановлении")
        self.assertEqual([item[3] for item in self.drain_alerts()], ["warning", "ok"])


if __name__ == "__main__":
    unittest.main()
