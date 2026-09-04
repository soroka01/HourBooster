"""Thread-safe SQLite storage for accounts, boost time, and the one-message UI."""

import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


class StorageError(ValueError):
    """Raised for a value that cannot be safely stored."""


@dataclass(frozen=True)
class Account:
    id: int
    title: str
    username: str
    password: str
    games: Tuple[int, ...]
    total_boost_seconds: int
    active_since: Optional[int]
    created_at: int
    updated_at: int


@dataclass(frozen=True)
class AccountStats:
    account_id: int
    total_seconds: int
    current_session_seconds: int
    completed_sessions: int
    is_active: bool


def parse_game_ids(raw_value: str) -> List[int]:
    """Convert a comma-separated list of Steam App IDs into validated integers."""
    values: List[int] = []
    seen = set()

    for part in raw_value.split(","):
        value = part.strip()
        if not value:
            continue
        if not value.isdigit() or int(value) <= 0:
            raise StorageError("Укажите Steam App ID положительными числами через запятую.")
        game_id = int(value)
        if game_id not in seen:
            values.append(game_id)
            seen.add(game_id)

    if not values:
        raise StorageError("Добавьте хотя бы один Steam App ID.")
    if len(values) > 50:
        raise StorageError("Для одного аккаунта можно указать не более 50 игр.")
    return values


class Database:
    """A small SQLite repository with explicit transactions and no global connection state."""

    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            str(database_path), check_same_thread=False, timeout=10
        )
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()

        with self._lock:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA busy_timeout = 5000")
            self._create_schema()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL COLLATE NOCASE UNIQUE,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                games_json TEXT NOT NULL,
                total_boost_seconds INTEGER NOT NULL DEFAULT 0,
                active_since INTEGER,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS boost_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                started_at INTEGER NOT NULL,
                ended_at INTEGER,
                duration_seconds INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_boost_sessions_account
                ON boost_sessions(account_id, started_at DESC);

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ui_sessions (
                chat_id INTEGER PRIMARY KEY,
                message_id INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            """
        )
        self._connection.commit()

    @staticmethod
    def _now(value: Optional[int] = None) -> int:
        return int(time.time()) if value is None else int(value)

    @staticmethod
    def _row_to_account(row: sqlite3.Row) -> Account:
        try:
            games = tuple(int(value) for value in json.loads(row["games_json"]))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise StorageError("Не удалось прочитать список игр аккаунта из базы данных.") from error

        return Account(
            id=int(row["id"]),
            title=str(row["title"]),
            username=str(row["username"]),
            password=str(row["password"]),
            games=games,
            total_boost_seconds=int(row["total_boost_seconds"]),
            active_since=(int(row["active_since"]) if row["active_since"] is not None else None),
            created_at=int(row["created_at"]),
            updated_at=int(row["updated_at"]),
        )

    @staticmethod
    def _validate_account(title: str, username: str, password: str, games: Sequence[int]) -> Tuple[str, str, str, List[int]]:
        title = title.strip()
        username = username.strip()
        if not title or len(title) > 48:
            raise StorageError("Название аккаунта должно содержать от 1 до 48 символов.")
        if not username or len(username) > 128:
            raise StorageError("Логин Steam должен содержать от 1 до 128 символов.")
        if not password or len(password) > 512:
            raise StorageError("Пароль Steam должен содержать от 1 до 512 символов.")

        normalised_games = []
        seen = set()
        for game in games:
            try:
                game_id = int(game)
            except (TypeError, ValueError) as error:
                raise StorageError("Steam App ID должен быть числом.") from error
            if game_id <= 0:
                raise StorageError("Steam App ID должен быть положительным.")
            if game_id not in seen:
                normalised_games.append(game_id)
                seen.add(game_id)

        if not normalised_games:
            raise StorageError("Добавьте хотя бы один Steam App ID.")
        if len(normalised_games) > 50:
            raise StorageError("Для одного аккаунта можно указать не более 50 игр.")
        return title, username, password, normalised_games

    def count_accounts(self) -> int:
        with self._lock:
            row = self._connection.execute("SELECT COUNT(*) AS total FROM accounts").fetchone()
            return int(row["total"])

    def list_accounts(self, page: int = 0, page_size: int = 6) -> Tuple[List[Account], int]:
        page = max(0, int(page))
        page_size = max(1, min(int(page_size), 20))
        with self._lock:
            total = self.count_accounts()
            rows = self._connection.execute(
                "SELECT * FROM accounts ORDER BY title COLLATE NOCASE, id LIMIT ? OFFSET ?",
                (page_size, page * page_size),
            ).fetchall()
        return [self._row_to_account(row) for row in rows], total

    def get_account(self, account_id: int) -> Optional[Account]:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM accounts WHERE id = ?", (int(account_id),)
            ).fetchone()
        return self._row_to_account(row) if row else None

    def create_account(self, title: str, username: str, password: str, games: Sequence[int]) -> Account:
        title, username, password, games = self._validate_account(title, username, password, games)
        now = self._now()
        try:
            with self._lock, self._connection:
                cursor = self._connection.execute(
                    """
                    INSERT INTO accounts(title, username, password, games_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (title, username, password, json.dumps(games), now, now),
                )
        except sqlite3.IntegrityError as error:
            raise StorageError("Аккаунт с таким названием уже существует.") from error
        account = self.get_account(int(cursor.lastrowid))
        if account is None:
            raise StorageError("Не удалось создать аккаунт.")
        return account

    def update_account(self, account_id: int, field: str, value: object) -> Account:
        account = self.get_account(account_id)
        if account is None:
            raise StorageError("Аккаунт не найден.")

        title = account.title
        username = account.username
        password = account.password
        games: Sequence[int] = account.games

        if field == "title":
            title = str(value)
        elif field == "username":
            username = str(value)
        elif field == "password":
            password = str(value)
        elif field == "games":
            games = value  # type: ignore[assignment]
        else:
            raise StorageError("Неизвестное поле аккаунта.")

        title, username, password, normalised_games = self._validate_account(title, username, password, games)
        try:
            with self._lock, self._connection:
                self._connection.execute(
                    """
                    UPDATE accounts
                    SET title = ?, username = ?, password = ?, games_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (title, username, password, json.dumps(normalised_games), self._now(), int(account_id)),
                )
        except sqlite3.IntegrityError as error:
            raise StorageError("Аккаунт с таким названием уже существует.") from error
        updated = self.get_account(account_id)
        if updated is None:
            raise StorageError("Не удалось обновить аккаунт.")
        return updated

    def delete_account(self, account_id: int) -> bool:
        with self._lock, self._connection:
            cursor = self._connection.execute("DELETE FROM accounts WHERE id = ?", (int(account_id),))
        return cursor.rowcount > 0

    def start_boost(self, account_id: int, started_at: Optional[int] = None) -> bool:
        now = self._now(started_at)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE accounts
                SET active_since = ?, updated_at = ?
                WHERE id = ? AND active_since IS NULL
                """,
                (now, now, int(account_id)),
            )
            if cursor.rowcount == 0:
                return False
            self._connection.execute(
                "INSERT INTO boost_sessions(account_id, started_at) VALUES (?, ?)",
                (int(account_id), now),
            )
        return True

    def stop_boost(self, account_id: int, ended_at: Optional[int] = None) -> int:
        now = self._now(ended_at)
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT active_since FROM accounts WHERE id = ?", (int(account_id),)
            ).fetchone()
            if row is None or row["active_since"] is None:
                return 0

            started_at = int(row["active_since"])
            duration = max(0, now - started_at)
            self._connection.execute(
                """
                UPDATE accounts
                SET total_boost_seconds = total_boost_seconds + ?, active_since = NULL, updated_at = ?
                WHERE id = ?
                """,
                (duration, now, int(account_id)),
            )
            self._connection.execute(
                """
                UPDATE boost_sessions
                SET ended_at = ?, duration_seconds = ?
                WHERE id = (
                    SELECT id FROM boost_sessions
                    WHERE account_id = ? AND ended_at IS NULL
                    ORDER BY id DESC LIMIT 1
                )
                """,
                (now, duration, int(account_id)),
            )
        return duration

    def get_account_stats(self, account_id: int, now: Optional[int] = None) -> AccountStats:
        account = self.get_account(account_id)
        if account is None:
            raise StorageError("Аккаунт не найден.")
        timestamp = self._now(now)
        current = max(0, timestamp - account.active_since) if account.active_since else 0
        with self._lock:
            row = self._connection.execute(
                "SELECT COUNT(*) AS total FROM boost_sessions WHERE account_id = ? AND ended_at IS NOT NULL",
                (int(account_id),),
            ).fetchone()
        return AccountStats(
            account_id=account.id,
            total_seconds=account.total_boost_seconds + current,
            current_session_seconds=current,
            completed_sessions=int(row["total"]),
            is_active=account.active_since is not None,
        )

    def recover_interrupted_sessions(self, now: Optional[int] = None) -> int:
        with self._lock:
            rows = self._connection.execute(
                "SELECT id FROM accounts WHERE active_since IS NOT NULL"
            ).fetchall()
        for row in rows:
            self.stop_boost(int(row["id"]), now)
        return len(rows)

    def get_setting(self, key: str) -> Optional[str]:
        with self._lock:
            row = self._connection.execute(
                "SELECT value FROM app_settings WHERE key = ?", (key,)
            ).fetchone()
        return str(row["value"]) if row else None

    def set_settings(self, values: Dict[str, str]) -> None:
        with self._lock, self._connection:
            self._connection.executemany(
                "INSERT INTO app_settings(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                values.items(),
            )

    def get_control_message(self, chat_id: int) -> Optional[int]:
        with self._lock:
            row = self._connection.execute(
                "SELECT message_id FROM ui_sessions WHERE chat_id = ?", (int(chat_id),)
            ).fetchone()
        return int(row["message_id"]) if row else None

    def set_control_message(self, chat_id: int, message_id: int) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO ui_sessions(chat_id, message_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    message_id = excluded.message_id,
                    updated_at = excluded.updated_at
                """,
                (int(chat_id), int(message_id), self._now()),
            )
