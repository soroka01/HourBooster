"""Application configuration that intentionally keeps only deployment secrets."""

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


class ConfigurationError(RuntimeError):
    """Raised when the local configuration cannot start the bot safely."""


@dataclass(frozen=True)
class AppConfig:
    telegram_token: str
    allowed_user_id: int
    database_path: Path


class ConfigManager:
    """Reads the local Telegram configuration and imports legacy account sections."""

    def __init__(self, config_file: str = "config/config.ini") -> None:
        self.path = Path(config_file)
        self.config = configparser.ConfigParser()

        if not self.path.is_file():
            raise ConfigurationError(
                "Не найден config/config.ini. Скопируйте config/config.ini.example и заполните Telegram-настройки."
            )

        self.config.read(str(self.path), encoding="utf-8")

    def get_app_config(self) -> AppConfig:
        try:
            token = self.config["telegram"]["bot_token"].strip()
            user_id = int(self.config["telegram"]["allowed_user_id"].strip())
        except (KeyError, ValueError) as error:
            raise ConfigurationError(
                "В секции [telegram] укажите bot_token и числовой allowed_user_id."
            ) from error

        if not token:
            raise ConfigurationError("bot_token не может быть пустым.")

        raw_database_path = self.config.get(
            "storage", "database_path", fallback="data/hour_booster.sqlite3"
        ).strip()
        database_path = Path(raw_database_path)
        if not database_path.is_absolute():
            database_path = self.path.parent.parent / database_path

        return AppConfig(
            telegram_token=token,
            allowed_user_id=user_id,
            database_path=database_path,
        )

    def get_legacy_accounts(self) -> List[Dict[str, object]]:
        """Return old account sections once so they can be migrated into SQLite."""
        accounts: List[Dict[str, object]] = []
        for section in self.config.sections():
            if not section.lower().startswith("account"):
                continue

            values = self.config[section]
            username = values.get("username", "").strip()
            password = values.get("password", "")
            games_raw = values.get("games", "")
            games: List[int] = []

            for game in games_raw.split(","):
                game = game.strip()
                if not game:
                    continue
                if not game.isdigit() or int(game) <= 0:
                    raise ConfigurationError(
                        "В старой секции {0} найден некорректный Steam App ID: {1}".format(section, game)
                    )
                games.append(int(game))

            if username and password and games:
                accounts.append(
                    {
                        "title": section,
                        "username": username,
                        "password": password,
                        "games": games,
                    }
                )

        return accounts
