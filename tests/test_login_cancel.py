"""login_token on the real gevent client: cancelling or timing out must not leave the thread stuck."""

import threading
import time
import types
import unittest
from unittest import mock

import gevent
from steam.enums import EResult

from src.steam import auth
from src.steam.auth import TokenSteamClient


def run_in_thread(target):
    outcome = {}

    def work():
        try:
            outcome["value"] = target()
        except Exception as error:
            outcome["error"] = error

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    return thread, outcome


class LoginCancelTests(unittest.TestCase):
    def test_cancel_interrupts_a_stuck_connect(self):
        cancelled = threading.Event()

        def stuck_logon():
            client = TokenSteamClient()
            client._pre_login = lambda: gevent.sleep(30)
            started = time.monotonic()
            result = client.login_token("user", 1, "token", cancelled=cancelled)
            return result, time.monotonic() - started

        thread, outcome = run_in_thread(stuck_logon)
        time.sleep(0.3)
        cancelled.set()
        thread.join(10)
        self.assertFalse(thread.is_alive())
        result, elapsed = outcome["value"]
        self.assertEqual(result, EResult.Timeout)
        self.assertLess(elapsed, 2.0)

    def test_deadline_still_applies_without_cancel(self):
        def slow_logon():
            client = TokenSteamClient()
            client._pre_login = lambda: gevent.sleep(30)
            return client.login_token("user", 1, "token")

        with mock.patch.object(auth, "LOGON_TIMEOUT", 0.3):
            thread, outcome = run_in_thread(slow_logon)
            thread.join(10)
        self.assertEqual(outcome["value"], EResult.Timeout)

    def test_successful_logon_returns_steams_result(self):
        def logon():
            client = TokenSteamClient()
            client._pre_login = lambda: EResult.OK
            client.wait_msg = lambda emsg, timeout=None: types.SimpleNamespace(
                body=types.SimpleNamespace(eresult=int(EResult.AccessDenied)))
            return client.login_token("user", 1, "token", cancelled=threading.Event())

        thread, outcome = run_in_thread(logon)
        thread.join(10)
        self.assertEqual(outcome["value"], EResult.AccessDenied)

    def test_errors_are_raised_to_the_caller(self):
        def broken():
            client = TokenSteamClient()

            def boom():
                raise OSError("network is down")

            client._pre_login = boom
            return client.login_token("user", 1, "token")

        thread, outcome = run_in_thread(broken)
        thread.join(10)
        self.assertIsInstance(outcome.get("error"), OSError)


if __name__ == "__main__":
    unittest.main()
