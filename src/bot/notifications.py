"""Separate owner alerts for unexpected Steam session interruptions."""

import asyncio
import html
import logging
import queue

from aiogram.exceptions import TelegramAPIError, TelegramNetworkError, TelegramRetryAfter, TelegramServerError

logger = logging.getLogger(__name__)


async def send_session_alerts(bot, owner_id: int, alerts: queue.Queue) -> None:
    while True:
        try:
            account_id, title, reason = alerts.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.5)
            continue
        text = "⚠️ <b>Steam: {0}</b>\n\n{1}".format(html.escape(title), html.escape(reason))
        delay = 2
        while True:
            try:
                # Do not change the control-message ID or navigate away from the open screen.
                await bot.send_message(owner_id, text, parse_mode="HTML")
                break
            except TelegramRetryAfter as error:
                await asyncio.sleep(error.retry_after)
            except (TelegramNetworkError, TelegramServerError):
                logger.warning("Уведомление об аккаунте %s ожидает восстановления Telegram; повтор через %s с", account_id, delay)
                await asyncio.sleep(delay)
                delay = min(60, delay * 2)
            except TelegramAPIError as error:
                logger.error("Не удалось отправить уведомление об аккаунте %s: %s", account_id, type(error).__name__)
                break
