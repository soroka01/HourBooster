"""Telegram command menu in the active interface language."""

from aiogram import Bot
from aiogram.types import BotCommand

from ..i18n import t


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description=t("bot.command.start")),
            BotCommand(command="menu", description=t("bot.command.menu")),
            BotCommand(command="cancel", description=t("bot.command.cancel")),
        ]
    )
