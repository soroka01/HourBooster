"""Steam Hour Booster entry point."""

import asyncio
import argparse
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from src.bot.access_middleware import AccessMiddleware
from src.bot.controller import BoosterController
from src.config_manager import load_config, ConfigurationError
from src.storage import Database
from src.steam.steam_manager import SteamSessionManager


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main(database_path: Path, setup: bool = False) -> None:
    configure_logging()
    logger = logging.getLogger(__name__)

    database = Database(database_path)
    try:
        app_config = load_config(database, setup)
    except BaseException:
        database.close()
        raise
    if setup:
        database.close()
        logger.info("Настройки Telegram сохранены в SQLite.")
        return
    recovered = database.recover_interrupted_sessions()

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
            BotCommand(command="cancel", description="✖️ Отменить ввод"),
        ]
    )

    logger.info("🎮 Steam Hour Booster запущен")
    try:
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await asyncio.to_thread(sessions.shutdown)
        await bot.session.close()
        database.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", action="store_true", help="Save Telegram settings to SQLite and exit")
    parser.add_argument("--database", type=Path,
                        default=Path(__file__).resolve().parent / "data" / "hour_booster.sqlite3",
                        help="SQLite database path")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.database, args.setup))
    except ConfigurationError as error:
        logging.basicConfig(level=logging.ERROR)
        logging.getLogger(__name__).error("Ошибка конфигурации: %s", error)
        raise SystemExit(1)
