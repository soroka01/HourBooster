import base64
import json
import os
import unittest

from src.i18n import t
from src.steam import guard


class GuardCodeTests(unittest.TestCase):
    ZERO_SECRET = base64.b64encode(bytes(20)).decode()

    def test_known_vectors(self):
        # Reference values produced by the Steam client algorithm (HMAC-SHA1 over time // 30).
        self.assertEqual(guard.generate_code(self.ZERO_SECRET, 1700000000), "THTN4")
        self.assertEqual(guard.generate_code(self.ZERO_SECRET, 1700000009), "THTN4")

    def test_code_shape(self):
        secret = base64.b64encode(os.urandom(20)).decode()
        for offset in range(0, 3000, 31):
            code = guard.generate_code(secret, 1700000000 + offset)
            self.assertEqual(len(code), 5)
            self.assertTrue(set(code) <= set("23456789BCDFGHJKMNPQRTVWXY"))

    def test_code_is_stable_inside_one_window(self):
        secret = base64.b64encode(os.urandom(20)).decode()
        base = 1700000010
        self.assertEqual(guard.generate_code(secret, base), guard.generate_code(secret, base + 19))
        self.assertNotEqual(guard.generate_code(secret, base), guard.generate_code(secret, base + 30))

    def test_next_window_is_in_the_future(self):
        for moment in (0.0, 1.5, 29.99, 30.0, 1700000017.3):
            self.assertGreater(guard.seconds_to_next_window(moment), 0)
            self.assertLessEqual(guard.seconds_to_next_window(moment), 31.0)

    def test_seconds_left_counts_down_to_the_window_edge(self):
        self.assertEqual(guard.code_seconds_left(1700000010.0), 30)  # a window starts here
        self.assertEqual(guard.code_seconds_left(1700000020.0), 20)
        self.assertEqual(guard.code_seconds_left(30.0), 30)
        self.assertEqual(guard.code_seconds_left(59.9), 1)
        for moment in range(0, 120):
            self.assertTrue(1 <= guard.code_seconds_left(moment) <= 30)


class SecretParsingTests(unittest.TestCase):
    def setUp(self):
        self.raw = os.urandom(20)
        self.secret = base64.b64encode(self.raw).decode()

    def test_bare_secret_with_whitespace(self):
        self.assertEqual(guard.extract_shared_secret("  {0}\r\n".format(self.secret)), self.secret)

    def test_mafile_json(self):
        body = json.dumps({"account_name": "user", "shared_secret": self.secret, "identity_secret": "x"})
        self.assertEqual(guard.extract_shared_secret(body), self.secret)

    def test_otpauth_uri(self):
        encoded = base64.b32encode(self.raw).decode().rstrip("=")
        uri = "otpauth://totp/Steam:user?secret={0}&issuer=Steam".format(encoded)
        self.assertEqual(guard.extract_shared_secret(uri), self.secret)

    def test_rejects_garbage(self):
        for value in ("", "   ", "not base64!", "AAAA", '{"account_name": "x"}', "{broken", "otpauth://totp/x"):
            with self.subTest(value=value):
                with self.assertRaises(guard.GuardSecretError):
                    guard.extract_shared_secret(value)

    def test_error_message_does_not_echo_the_secret(self):
        with self.assertRaises(guard.GuardSecretError) as caught:
            guard.extract_shared_secret(self.secret[:-4] + "!!!!")
        self.assertNotIn(self.secret[:10], str(caught.exception))


class MaFileTests(unittest.TestCase):
    def setUp(self):
        self.secret = base64.b64encode(os.urandom(20)).decode()

    def test_parse_mafile(self):
        result = guard.parse_mafile(json.dumps({"account_name": " Login ", "shared_secret": self.secret}))
        self.assertEqual(result.account_name, "Login")
        self.assertEqual(result.shared_secret, self.secret)

    def test_parse_mafile_with_bom(self):
        text = "﻿" + json.dumps({"account_name": "a", "shared_secret": self.secret})
        self.assertEqual(guard.parse_mafile(text).account_name, "a")

    def test_encrypted_mafile_is_reported(self):
        with self.assertRaises(guard.GuardSecretError) as caught:
            guard.parse_mafile("kJ3x9+encrypted-blob==")
        self.assertEqual(str(caught.exception), t("steam.guard.mafile_unreadable"))

    def test_missing_fields(self):
        for content in ('{"shared_secret": "%s"}' % self.secret, '{"account_name": "a"}', "[]", ""):
            with self.subTest(content=content):
                with self.assertRaises(guard.GuardSecretError):
                    guard.parse_mafile(content)


if __name__ == "__main__":
    unittest.main()
