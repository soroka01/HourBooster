import base64
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.steam.guard import GuardSecretError
from src.storage import Database, StorageError


class DatabaseSharedSecretTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "test.sqlite3"
        self.secret = base64.b64encode(os.urandom(20)).decode()

    def open(self):
        database = Database(self.path)
        self.addCleanup(database.close)
        return database

    def test_old_database_is_migrated_without_losing_accounts(self):
        connection = sqlite3.connect(str(self.path))
        connection.executescript(
            """
            CREATE TABLE accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL COLLATE NOCASE UNIQUE,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                games_json TEXT NOT NULL,
                total_boost_seconds INTEGER NOT NULL DEFAULT 0,
                active_since INTEGER,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                custom_game_name TEXT NOT NULL DEFAULT ''
            );
            INSERT INTO accounts(title, username, password, games_json, created_at, updated_at)
            VALUES ('Old', 'olduser', 'pw', '[730]', 1, 1);
            """
        )
        connection.commit()
        connection.close()

        database = self.open()
        account = database.find_accounts_by_username("OLDUSER")[0]
        self.assertEqual(account.title, "Old")
        self.assertEqual(account.shared_secret, "")
        self.assertFalse(account.autostart)

    def test_set_replace_and_clear_secret(self):
        database = self.open()
        account = database.create_account("Main", "login", "pw", [730])
        self.assertEqual(account.shared_secret, "")

        updated = database.update_account(account.id, "shared_secret", "  {0}\n".format(self.secret))
        self.assertEqual(updated.shared_secret, self.secret)
        self.assertEqual(database.get_account(account.id).shared_secret, self.secret)

        other = base64.b64encode(os.urandom(20)).decode()
        self.assertEqual(database.update_account(account.id, "shared_secret", other).shared_secret, other)
        self.assertEqual(database.update_account(account.id, "shared_secret", "").shared_secret, "")

    def test_other_updates_keep_the_secret(self):
        database = self.open()
        account = database.create_account("Main", "login", "pw", [730])
        database.update_account(account.id, "shared_secret", self.secret)
        database.update_account(account.id, "games", [570])
        database.update_account(account.id, "password", "new")
        self.assertEqual(database.get_account(account.id).shared_secret, self.secret)

    def test_invalid_secret_is_rejected_and_not_stored(self):
        database = self.open()
        account = database.create_account("Main", "login", "pw", [730])
        with self.assertRaises(GuardSecretError):
            database.update_account(account.id, "shared_secret", "not base64!")
        self.assertEqual(database.get_account(account.id).shared_secret, "")

    def test_secret_and_password_are_hidden_from_repr(self):
        database = self.open()
        account = database.create_account("Main", "login", "hunter2", [730])
        account = database.update_account(account.id, "shared_secret", self.secret)
        text = repr(account)
        self.assertNotIn("hunter2", text)
        self.assertNotIn(self.secret, text)

    def test_find_accounts_by_username_is_case_insensitive(self):
        database = self.open()
        first = database.create_account("A", "Login", "pw", [730])
        database.create_account("B", "other", "pw", [730])
        found = database.find_accounts_by_username("  login ")
        self.assertEqual([item.id for item in found], [first.id])
        self.assertEqual(database.find_accounts_by_username("missing"), [])

    def test_autostart_flag_is_remembered_and_survives_other_edits(self):
        database = self.open()
        first = database.create_account("A", "a", "pw", [730])
        second = database.create_account("B", "b", "pw", [730])
        self.assertFalse(first.autostart)
        self.assertEqual(database.list_autostart_accounts(), [])

        database.set_autostart(first.id, True)
        database.update_account(first.id, "games", [570])
        self.assertEqual([item.id for item in database.list_autostart_accounts()], [first.id])
        self.assertTrue(database.get_account(first.id).autostart)
        self.assertFalse(database.get_account(second.id).autostart)

        database.set_autostart(first.id, False)
        self.assertEqual(database.list_autostart_accounts(), [])

    def test_unknown_field_still_rejected(self):
        database = self.open()
        account = database.create_account("Main", "login", "pw", [730])
        with self.assertRaises(StorageError):
            database.update_account(account.id, "nope", "x")


if __name__ == "__main__":
    unittest.main()
