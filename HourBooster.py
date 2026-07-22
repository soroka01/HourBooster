"""Steam Hour Booster entry point."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from src.bot.access_middleware import AccessMiddleware
from src.bot.controller import BoosterController
from src.config_manager import ConfigManager, ConfigurationError
from src.storage import Database
from src.steam.steam_manager import SteamSessionManager


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)

    config_manager = ConfigManager()
    app_config = config_manager.get_app_config()
    database = Database(app_config.database_path)
    migrated = database.migrate_legacy_accounts(config_manager.get_legacy_accounts())
    recovered = database.recover_interrupted_sessions()

    if migrated:
        logger.info("Перенесено старых аккаунтов в SQLite: %s", migrated)
    if recovered:
        logger.info("Закрыто прерванных сессий после перезапуска: %s", recovered)

    bot = Bot(token=app_config.telegram_token)
    dispatcher = Dispatcher()
    sessions = SteamSessionManager(database)
    controller = BoosterController(bot, database, sessions)

    middleware = AccessMiddleware(app_config.allowed_user_id)
    dispatcher.message.middleware(middleware)
    dispatcher.callback_query.middleware(middleware)
    dispatcher.include_router(controller.router)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="🎮 Открыть аккаунты"),
            BotCommand(command="menu", description="🏠 Главное меню"),
            BotCommand(command="help", description="❓ Помощь"),
            BotCommand(command="cancel", description="✖️ Отменить ввод"),
        ]
    )

    logger.info("🎮 Steam Hour Booster запущен")
    try:
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await bot.session.close()
        database.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ConfigurationError as error:
        logging.basicConfig(level=logging.ERROR)
        logging.getLogger(__name__).error("Ошибка конфигурации: %s", error)
