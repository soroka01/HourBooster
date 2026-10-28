"""Separate owner alerts for Steam session problems and recoveries."""

import asyncio
import html
import logging
import queue

from aiogram.exceptions import TelegramAPIError, TelegramNetworkError, TelegramRetryAfter, TelegramServerError

logger = logging.getLogger(__name__)


async def send_session_alerts(bot, owner_id: int, alerts: queue.Queue) -> None:
    while True:
        try:
            item = alerts.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.5)
            continue
        # Older producers put 3-tuples without a kind; those are warnings.
        account_id, title, reason = item[:3]
        kind = item[3] if len(item) > 3 else "warning"
        icon = "✅" if kind == "ok" else "⚠️"
        text = "{0} <b>Steam: {1}</b>\n\n{2}".format(icon, html.escape(title), html.escape(reason))
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
