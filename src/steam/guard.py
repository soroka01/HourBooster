"""Steam Guard mobile-authenticator helpers: shared_secret parsing, TOTP codes and Steam time."""

import base64
import binascii
import json
import re
import threading
import time
from typing import NamedTuple, Optional

from steam.guard import generate_twofactor_code_for_time, get_time_offset

from ..i18n import t

CODE_PERIOD = 30
_OTPAUTH_SECRET = re.compile(r"[?&]secret=([A-Za-z2-7]+)")


class GuardSecretError(ValueError):
    """Raised when a Steam Guard secret or maFile cannot be used."""


class MaFile(NamedTuple):
    account_name: str
    shared_secret: str


def normalize_shared_secret(value: str) -> str:
    """Return the canonical base64 form of a 20-byte-ish shared_secret."""
    text = (value or "").strip()
    try:
        raw = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        raise GuardSecretError(t("steam.guard.secret_not_base64")) from None
    if not 10 <= len(raw) <= 64:
        raise GuardSecretError(t("steam.guard.secret_bad_length"))
    return base64.b64encode(raw).decode("ascii")


def parse_mafile(text: str) -> MaFile:
    """Read account_name and shared_secret from the text of a Steam Desktop Authenticator maFile."""
    try:
        data = json.loads((text or "").strip().lstrip("﻿"))
    except ValueError:
        raise GuardSecretError(t("steam.guard.mafile_unreadable")) from None
    if not isinstance(data, dict):
        raise GuardSecretError(t("steam.guard.mafile_not_object"))
    account_name = data.get("account_name")
    secret = data.get("shared_secret")
    if not isinstance(account_name, str) or not account_name.strip():
        raise GuardSecretError(t("steam.guard.mafile_no_account"))
    if not isinstance(secret, str) or not secret:
        raise GuardSecretError(t("steam.guard.mafile_no_secret"))
    return MaFile(account_name.strip(), normalize_shared_secret(secret))


def extract_shared_secret(text: str) -> str:
    """Accept a bare shared_secret, an SDA maFile JSON body or an otpauth:// URI."""
    body = (text or "").strip().lstrip("﻿")
    if not body:
        raise GuardSecretError(t("steam.guard.empty"))
    if body.startswith("{"):
        return parse_mafile(body).shared_secret
    if body.lower().startswith("otpauth://"):
        match = _OTPAUTH_SECRET.search(body)
        if not match:
            raise GuardSecretError(t("steam.guard.otpauth_no_secret"))
        encoded = match.group(1).upper()
        try:
            raw = base64.b32decode(encoded + "=" * (-len(encoded) % 8))
        except (binascii.Error, ValueError):
            raise GuardSecretError(t("steam.guard.otpauth_unreadable")) from None
        return normalize_shared_secret(base64.b64encode(raw).decode("ascii"))
    return normalize_shared_secret(body)


def generate_code(shared_secret: str, timestamp: Optional[float] = None) -> str:
    moment = int(time.time() if timestamp is None else timestamp)
    return generate_twofactor_code_for_time(base64.b64decode(shared_secret), moment)


def seconds_to_next_window(timestamp: float) -> float:
    """Time until the next code period starts (plus a second of slack for network latency)."""
    return CODE_PERIOD - (timestamp % CODE_PERIOD) + 1.0


class SteamClock:
    """Steam server time, cached; Guard codes are rejected when the local clock drifts."""

    def __init__(self, ttl: float = 3600.0, retry: float = 60.0) -> None:
        self._ttl = ttl
        self._retry = retry
        self._offset = 0
        self._valid_until = 0.0
        self._lock = threading.Lock()

    def now(self, force: bool = False) -> float:
        with self._lock:
            moment = time.time()
            if force or moment >= self._valid_until:
                fetched = get_time_offset()
                if fetched is not None:
                    self._offset = fetched
                    self._valid_until = moment + self._ttl
                else:
                    self._valid_until = moment + self._retry
            return moment + self._offset


steam_clock = SteamClock()
