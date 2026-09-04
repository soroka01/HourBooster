"""Steam AuthenticationService credentials/Guard flow and CM token login."""

import base64
import json

import requests
from Cryptodome.Cipher import PKCS1_v1_5
from Cryptodome.PublicKey import RSA
from gevent import Timeout
from steam.client import SteamClient
from steam.core.msg import MsgProto
from steam.enums import EResult, EOSType
from steam.enums.emsg import EMsg
from steam.steamid import SteamID


class AuthError(Exception):
    def __init__(self, message: str, code: int = 0):
        super().__init__(message)
        self.code = code


class SteamAuth:
    def __init__(self):
        self.http = requests.Session()
        self.client_id = None
        self.request_id = None
        self.steam_id = None
        self.interval = 2.0
        self.code_type = None

    def close(self):
        self.http.close()
        self.client_id = self.request_id = None

    def _call(self, method, payload, get=False):
        url = "https://api.steampowered.com/IAuthenticationService/{0}/v1/".format(method)
        try:
            if get:
                response = self.http.get(url, params=payload, timeout=15)
            else:
                response = self.http.post(url, data={"input_json": json.dumps(payload)}, timeout=15)
            code = int(response.headers.get("x-eresult", "1"))
            if code != 1:
                messages = {
                    5: "Steam не принял логин или пароль в современном API (код 5).",
                    65: "Неверный код Steam Guard. Введите новый код.",
                    88: "Неверный код Steam Guard. Введите новый код.",
                    84: "Steam ограничил попытки входа. Повторите позже.",
                    27: "Запрос входа истёк. Запустите аккаунт заново.",
                }
                raise AuthError(messages.get(code, "Steam отклонил авторизацию (код {0}).".format(code)), code)
            response.raise_for_status()
            body = response.json()["response"]
            if not isinstance(body, dict):
                raise ValueError
            return body
        except (requests.RequestException, ValueError, KeyError):
            # HTTP exceptions may include request URLs; never expose auth payloads.
            raise AuthError("Не удалось связаться с API авторизации Steam. Повторите позже.") from None

    def begin(self, username, password):
        key = self._call("GetPasswordRSAPublicKey", {"account_name": username}, get=True)
        rsa = RSA.construct((int(key["publickey_mod"], 16), int(key["publickey_exp"], 16)))
        encrypted = PKCS1_v1_5.new(rsa).encrypt(password.encode("utf-8"))
        body = self._call("BeginAuthSessionViaCredentials", {
            "account_name": username,
            "encrypted_password": base64.b64encode(encrypted).decode("ascii"),
            "encryption_timestamp": key["timestamp"],
            "platform_type": 1,
            "persistence": 1,
            "website_id": "Client",
            "device_friendly_name": "Steam Hour Booster",
            "device_details": {"device_friendly_name": "Steam Hour Booster", "platform_type": 1,
                               "os_type": int(EOSType.Windows10)},
        })
        self.client_id, self.request_id = body["client_id"], body["request_id"]
        self.steam_id = int(body["steamid"])
        self.interval = max(1.0, min(float(body.get("interval", 2)), 10.0))
        methods = {item["confirmation_type"] for item in body.get("allowed_confirmations", [])}
        self.code_type = 3 if 3 in methods else 2 if 2 in methods else None
        if self.code_type == 3:
            return "mobile"
        if self.code_type == 2:
            return "email"
        if 1 in methods:
            return None
        if methods & {4, 5}:
            return "confirmation"
        raise AuthError("Steam запросил неподдерживаемый способ подтверждения входа.")

    def submit_code(self, code):
        if self.code_type is None:
            raise AuthError("Подтвердите вход в приложении Steam или по ссылке из письма.")
        self._call("UpdateAuthSessionWithSteamGuardCode", {
            "client_id": self.client_id, "steamid": str(self.steam_id),
            "code": code, "code_type": self.code_type,
        })

    def poll(self):
        body = self._call("PollAuthSessionStatus", {
            "client_id": self.client_id, "request_id": self.request_id,
        })
        self.client_id = body.get("new_client_id") or self.client_id
        return body.get("refresh_token")


class TokenSteamClient(SteamClient):
    def set_played_games(self, app_ids, custom_name=""):
        if not custom_name:
            self.games_played(list(app_ids))
            return
        # Non-Steam shortcut ID used by node-steam-user for named games.
        games = [{"game_id": 15190414816125648896, "game_extra_info": custom_name}]
        games.extend({"game_id": int(app_id)} for app_id in app_ids)
        self.current_games_played = list(app_ids)
        self.send(MsgProto(EMsg.ClientGamesPlayed), {"games_played": games})

    def login_token(self, username, steam_id, refresh_token):
        # CM requires a refresh token issued for platform SteamClient, not a web access token.
        try:
            with Timeout(45):
                result = self._pre_login()
                if result != EResult.OK:
                    return result
                self.username = username
                message = MsgProto(EMsg.ClientLogon)
                message.header.steamid = SteamID(steam_id)
                message.body.protocol_version = 65580
                message.body.client_package_version = 1561159470
                message.body.client_os_type = EOSType.Windows10
                message.body.client_language = "english"
                message.body.should_remember_password = False
                message.body.supports_rate_limit_response = True
                message.body.chat_mode = self.chat_mode
                message.body.access_token = refresh_token
                self.send(message)
                response = self.wait_msg(EMsg.ClientLogOnResponse, timeout=30)
                if response and response.body.eresult == EResult.OK:
                    self.sleep(0.5)
                return EResult(response.body.eresult) if response else EResult.Timeout
        except Timeout:
            return EResult.Timeout
