"""Allowlisted login diagnostics: never log credentials or protocol payloads."""

import logging
import platform
from importlib.metadata import version

from steam.enums.emsg import EMsg

logger = logging.getLogger(__name__)


def attach_login_diagnostics(client, account_id: int) -> None:
    logger.info("Steam login account=%s python=%s steam=%s", account_id,
                platform.python_version(), version("steam"))
    for event in (client.EVENT_CONNECTED, client.EVENT_CHANNEL_SECURED,
                  client.EVENT_DISCONNECTED):
        client.on(event, lambda *args, event=event: logger.info(
            "Steam account=%s event=%s", account_id, event))

    def log_response(message):
        body = message.body
        logger.info("Steam account=%s logon_response eresult=%s extended=%s",
                    account_id, body.eresult,
                    getattr(body, "eresult_extended", None))

    client.on(EMsg.ClientLogOnResponse, log_response)
