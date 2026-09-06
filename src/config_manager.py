"""Telegram settings stored alongside accounts in SQLite."""

import sys
from dataclasses import dataclass

from aiogram.utils.token import TokenValidationError, validate_token

from .storage import Database


class ConfigurationError(ValueError):
    """Missing or invalid Telegram settings."""


@dataclass(frozen=True)
class AppConfig:
    telegram_token: str
    allowed_user_id: int


def load_config(database: Database, setup: bool = False) -> AppConfig:
    token = database.get_setting("telegram_token")
    owner = database.get_setting("allowed_user_id")
    if setup or not token or not owner:
        if not sys.stdin.isatty():
            raise ConfigurationError("Запустите HourBooster.py --setup в интерактивной консоли.")
        try:
            token = input("Telegram bot token: ").strip()
            owner = input("Telegram owner user ID: ").strip()
        except (EOFError, KeyboardInterrupt):
            raise ConfigurationError("Настройка отменена.") from None
    try:
        validate_token(token)
        user_id = int(owner)
        if user_id <= 0:
            raise ValueError
    except (ValueError, TypeError, TokenValidationError):
        raise ConfigurationError("Укажите корректный токен Telegram и положительный user ID. Используйте --setup.") from None
    database.set_settings({"telegram_token": token, "allowed_user_id": str(user_id)})
    return AppConfig(token, user_id)
