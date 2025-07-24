from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from ..config_manager import ConfigManager

class AccessMiddleware(BaseMiddleware):    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.allowed_user_id = config_manager.get_allowed_user_id()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем user_id из события
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        
        # Если user_id не определен, пропускаем
        if user_id is None:
            return await handler(event, data)
        
        # Проверяем доступ
        if user_id != self.allowed_user_id:
            # Отправляем сообщение о том, что бот доступен на GitHub
            if isinstance(event, Message):
                await event.answer(
                    "🚫 *Доступ ограничен*\n\n"
                    "Этот бот предназначен для личного использования.\n\n"
                    "📂 Исходный код доступен на GitHub:\n"
                    "https://github.com/soroka01/HourBooster\n\n"
                    "🔧 Вы можете развернуть свою копию бота, "
                    "следуя инструкциям в README.md",
                    parse_mode='Markdown'
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "🚫 Доступ ограничен. Бот доступен на GitHub.",
                    show_alert=True
                )
            return
        
        # Если пользователь авторизован, продолжаем обработку
        return await handler(event, data)
