"""Telegram settings stored alongside accounts in SQLite."""

import sys
from dataclasses import dataclass

from aiogram.utils.token import TokenValidationError, validate_token

from .i18n import LANGUAGE_SETTING, get_language, normalize_language, set_language, t
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
    language = get_language()
    settings_requested = setup or not token or not owner
    if settings_requested:
        if not sys.stdin.isatty():
            raise ConfigurationError(t("core.setup.not_interactive"))
        try:
            # The language is asked first (in the currently active language) so the rest of the dialogue uses it.
            answer = input(t("core.setup.prompt.language", current=language)).strip()
            if answer:
                language = normalize_language(answer)
            set_language(language)
            token = input(t("core.setup.prompt.token")).strip()
            owner = input(t("core.setup.prompt.owner")).strip()
        except (EOFError, KeyboardInterrupt):
            raise ConfigurationError(t("core.setup.cancelled")) from None
    try:
        validate_token(token)
        user_id = int(owner)
        if user_id <= 0:
            raise ValueError
    except (ValueError, TypeError, TokenValidationError):
        raise ConfigurationError(t("core.setup.invalid")) from None
    settings = {"telegram_token": token, "allowed_user_id": str(user_id)}
    if settings_requested:
        settings[LANGUAGE_SETTING] = language
    database.set_settings(settings)
    return AppConfig(token, user_id)
