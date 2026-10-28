"""Steam Hour Booster entry point."""

import asyncio
import argparse
import logging
from contextlib import suppress
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNotFound, TelegramUnauthorizedError

from src.bot.access_middleware import AccessMiddleware
from src.bot.commands import set_bot_commands
from src.bot.controller import BoosterController
from src.bot.notifications import send_session_alerts
from src.config_manager import load_config, ConfigurationError
from src.i18n import LANGUAGE_SETTING, set_language, t
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
    set_language(database.get_setting(LANGUAGE_SETTING))
    try:
        app_config = load_config(database, setup)
    except BaseException:
        database.close()
        raise
    if setup:
        database.close()
        logger.info(t("core.main.setup_saved"))
        return
    recovered = database.recover_interrupted_sessions()

    if recovered:
        logger.info(t("core.main.recovered", count=recovered))

    bot = Bot(token=app_config.telegram_token)
    dispatcher = Dispatcher()
    sessions = SteamSessionManager(database)
    controller = BoosterController(bot, database, sessions)

    middleware = AccessMiddleware(app_config.allowed_user_id)
    dispatcher.message.middleware(middleware)
    dispatcher.callback_query.middleware(middleware)
    dispatcher.include_router(controller.router)

    notifications = None
    try:
        try:
            await set_bot_commands(bot)
        except (TelegramNotFound, TelegramUnauthorizedError):
            raise ConfigurationError(t("core.main.commands_rejected")) from None
        logger.info(t("core.main.started"))
        notifications = asyncio.create_task(send_session_alerts(bot, app_config.allowed_user_id, sessions.alerts))
        sessions.autostart(app_config.allowed_user_id)
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        try:
            await asyncio.to_thread(sessions.shutdown)
            if notifications is not None:
                notifications.cancel()
                with suppress(asyncio.CancelledError):
                    await notifications
        finally:
            try:
                await bot.session.close()
            finally:
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
        logging.getLogger(__name__).error(t("core.main.config_error", error=error))
        raise SystemExit(1)
