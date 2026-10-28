"""Interface language: message catalogs and the process-wide language setting.

Every user-visible text (Telegram screens, alerts, errors, console output) is a catalog key resolved
by ``t()`` at call time, so a language switch applies to everything shown afterwards.
"""

from typing import Dict, Optional

from .locales import bot_en, bot_ru, core_en, core_ru, steam_en, steam_ru

DEFAULT_LANGUAGE = "en"
LANGUAGES = ("en", "ru")
LANGUAGE_SETTING = "language"

_ALIASES = {
    "en": "en", "eng": "en", "english": "en", "ru": "ru", "rus": "ru", "russian": "ru",
    # Cyrillic spellings, escaped so that the sources stay ASCII-only.
    "\u0440\u0443": "ru", "\u0440\u0443\u0441": "ru", "\u0440\u0443\u0441\u0441\u043a\u0438\u0439": "ru",
    "\u0430\u043d\u0433": "en", "\u0430\u043d\u0433\u043b": "en", "\u0430\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u0438\u0439": "en",
}

CATALOGS: Dict[str, Dict[str, str]] = {
    "en": {**core_en.MESSAGES, **steam_en.MESSAGES, **bot_en.MESSAGES},
    "ru": {**core_ru.MESSAGES, **steam_ru.MESSAGES, **bot_ru.MESSAGES},
}

_language = DEFAULT_LANGUAGE


def normalize_language(value: Optional[str]) -> str:
    """Map a stored or typed value ("RU", "russian", ...) to a supported code; unknown means English."""
    return _ALIASES.get((value or "").strip().lower(), DEFAULT_LANGUAGE)


def set_language(value: Optional[str]) -> str:
    global _language
    _language = normalize_language(value)
    return _language


def get_language() -> str:
    return _language


def other_language(value: Optional[str] = None) -> str:
    return "ru" if normalize_language(value or _language) == "en" else "en"


def t(key: str, **params: object) -> str:
    """Text for ``key`` in the active language (English if the key is missing there), formatted with ``params``."""
    text = CATALOGS[_language].get(key)
    if text is None:
        text = CATALOGS[DEFAULT_LANGUAGE].get(key, key)
    return text.format(**params)


class Text:
    """A message resolved when it is displayed, so texts stored before a language switch follow the switch."""

    def __init__(self, key: str, **params: object) -> None:
        self.key = key
        self.params = params

    def __str__(self) -> str:
        return t(self.key, **self.params)

    def __repr__(self) -> str:
        return "Text({0!r})".format(self.key)
