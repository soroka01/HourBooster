"""Read-only credential checks and one optional Steam login, without playing games."""

import argparse
import base64
import json
import logging
import sqlite3

import requests
from Cryptodome.Cipher import PKCS1_v1_5
from Cryptodome.PublicKey import RSA
from gevent import Timeout
from steam.client import SteamClient

from src.config_manager import ConfigManager
from src.steam.diagnostics import attach_login_diagnostics


def check_modern_auth(username: str, password: str) -> int:
    """Validate credentials and report Guard methods, without polling for tokens."""
    root = "https://api.steampowered.com/IAuthenticationService/"
    with requests.Session() as session:
        response = session.get(root + "GetPasswordRSAPublicKey/v1/",
                               params={"account_name": username}, timeout=20)
        response.raise_for_status()
        key = response.json()["response"]
        public_key = RSA.construct((int(key["publickey_mod"], 16),
                                    int(key["publickey_exp"], 16)))
        encrypted = PKCS1_v1_5.new(public_key).encrypt(password.encode("utf-8"))
        payload = {
            "account_name": username,
            "encrypted_password": base64.b64encode(encrypted).decode("ascii"),
            "encryption_timestamp": key["timestamp"],
            "remember_login": False,
            "platform_type": 2,
            "persistence": 0,
            "website_id": "Community",
            "device_friendly_name": "HourBooster login diagnostic",
        }
        response = session.post(root + "BeginAuthSessionViaCredentials/v1/",
                                data={"input_json": json.dumps(payload)}, timeout=20)
        result = response.headers.get("x-eresult")
        print("modern_auth_http:", response.status_code, "eresult:", result)
        response.raise_for_status()
        body = response.json().get("response", {})
        print("auth_session_created:", bool(body.get("client_id")),
              "confirmation_types:", [item.get("confirmation_type")
                                      for item in body.get("allowed_confirmations", [])])
        return 0 if result == "1" and body.get("client_id") else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("account_id", type=int)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--login", action="store_true", help="Attempt one legacy client login")
    mode.add_argument("--modern", action="store_true",
                      help="Check modern web authentication; may trigger a Steam Guard notification")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s")
    config = ConfigManager()
    path = config.get_app_config().database_path.resolve()
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        row = connection.execute("SELECT username, password FROM accounts WHERE id = ?",
                                 (args.account_id,)).fetchone()
    finally:
        connection.close()
    if row is None:
        print("Account not found")
        return 1
    username, password = row
    print("account_id:", args.account_id, "source: SQLite", flush=True)
    print("password_present:", bool(password), "edge_whitespace:", password != password.strip(),
          "control_characters:", any(ord(c) < 32 for c in password), flush=True)
    if args.modern:
        try:
            return check_modern_auth(username, password)
        except Exception as error:
            print("Modern auth exception type:", type(error).__name__)
            return 1
    if not args.login:
        return 0
    client = SteamClient()
    attach_login_diagnostics(client, args.account_id)
    try:
        with Timeout(60):
            result = client.login(username=username, password=password)
        print("login_result:", result.name, "code:", int(result), flush=True)
        return 0 if int(result) == 1 else 1
    except Timeout:
        print("Login timed out after 60 seconds")
        return 1
    except Exception as error:
        # Exception messages may contain credentials or protocol data.
        print("Login exception type:", type(error).__name__)
        return 1
    finally:
        client.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
