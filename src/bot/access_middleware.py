"""Restrict all bot interactions to the owner configured locally."""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class AccessMiddleware(BaseMiddleware):
    def __init__(self, allowed_user_id: int) -> None:
        self.allowed_user_id = int(allowed_user_id)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            user_id = event.from_user.id

        if user_id is None or user_id == self.allowed_user_id:
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            await event.answer("🚫 Доступ только у владельца бота.", show_alert=True)
        elif isinstance(event, Message):
            await event.answer("🚫 Этот бот настроен для личного использования владельцем.")
        return None
