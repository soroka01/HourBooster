"""One-message Telegram UI primitives and screen builders."""

import asyncio
import html
import logging
import math
import time
from contextvars import ContextVar
from typing import Awaitable, Callable, Dict, Iterable, Optional

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError,
    TelegramRetryAfter, TelegramServerError,
)
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..i18n import get_language, other_language, t
from ..storage import Account, AccountStats, Database
from ..steam.steam_manager import SessionSnapshot, SessionStatus

logger = logging.getLogger(__name__)

PAGE_SIZE = 6


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days:
        return t("bot.duration.days_clock", days=days, hours=hours, minutes=minutes, seconds=seconds)
    return "{0:02d}:{1:02d}:{2:02d}".format(hours, minutes, seconds)


def format_outage(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds >= 3600:
        return format_duration(seconds)
    return "{0:02d}:{1:02d}".format(*divmod(seconds, 60))


def status_label(snapshot: SessionSnapshot) -> str:
    keys = {
        SessionStatus.ACTIVE: "bot.status.active",
        SessionStatus.PAUSED: "bot.status.paused",
        SessionStatus.CONNECTING: "bot.status.connecting",
        SessionStatus.RECONNECTING: "bot.status.reconnecting",
        SessionStatus.AWAITING_GUARD: "bot.status.awaiting_guard",
        SessionStatus.AWAITING_EMAIL: "bot.status.awaiting_email",
        SessionStatus.STOPPING: "bot.status.stopping",
        SessionStatus.ERROR: "bot.status.error",
        SessionStatus.STOPPED: "bot.status.stopped",
        SessionStatus.IDLE: "bot.status.stopped",
    }
    return t(keys.get(snapshot.status, "bot.status.unknown"))


def dashboard_keyboard(accounts: Iterable[Account], page: int, total: int) -> InlineKeyboardMarkup:
    rows = []
    for account in accounts:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🎮 {0}".format(account.title[:40]),
                    callback_data="account:{0}:{1}".format(account.id, page),
                )
            ]
        )

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if total_pages > 1:
        navigation = []
        if page > 0:
            navigation.append(InlineKeyboardButton(text="⬅️", callback_data="home:{0}".format(page - 1)))
        navigation.append(InlineKeyboardButton(text="📄 {0}/{1}".format(page + 1, total_pages), callback_data="noop"))
        if page + 1 < total_pages:
            navigation.append(InlineKeyboardButton(text="➡️", callback_data="home:{0}".format(page + 1)))
        rows.append(navigation)

    rows.append([InlineKeyboardButton(text=t("bot.button.add_account"), callback_data="new")])
    if total:
        rows.append([InlineKeyboardButton(text=t("bot.button.import_guard"), callback_data="import_guard")])
    language_name = t("bot.language.name." + other_language(get_language()))
    rows.append([InlineKeyboardButton(text=t("bot.button.language", name=language_name), callback_data="lang")])
    rows.append([InlineKeyboardButton(text=t("bot.button.refresh"), callback_data="home:{0}".format(page))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def import_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("bot.button.done"), callback_data="home:0")],
            [InlineKeyboardButton(text=t("bot.button.cancel"), callback_data="cancel")],
        ]
    )


def dashboard_text(rows: Iterable[tuple], total_accounts: int) -> str:
    rows = list(rows)
    active = sum(1 for _, _, snapshot in rows if snapshot.status == SessionStatus.ACTIVE)
    total_seconds = sum(stats.total_seconds for _, stats, _ in rows)
    text = t("bot.dashboard.header")
    text += t("bot.dashboard.counts", total=total_accounts, active=active)
    text += t("bot.dashboard.time", duration=format_duration(total_seconds))

    if not rows:
        text += t("bot.dashboard.empty")
        return text

    text += t("bot.dashboard.choose")
    for account, stats, snapshot in rows:
        text += "\n{0} <b>{1}</b>\n".format(status_label(snapshot).split(" ")[0], html.escape(account.title))
        text += t("bot.dashboard.row_stats", duration=format_duration(stats.total_seconds), games=len(account.games))
    return text


def account_keyboard(account_id: int, snapshot: SessionSnapshot, page: int) -> InlineKeyboardMarkup:
    if snapshot.status in (SessionStatus.ACTIVE, SessionStatus.CONNECTING, SessionStatus.RECONNECTING,
                           SessionStatus.STOPPING, SessionStatus.PAUSED):
        primary = InlineKeyboardButton(text=t("bot.button.stop"), callback_data="stop:{0}:{1}".format(account_id, page))
    elif snapshot.status in (SessionStatus.AWAITING_GUARD, SessionStatus.AWAITING_EMAIL):
        primary = InlineKeyboardButton(text=t("bot.button.enter_code"), callback_data="guard:{0}:{1}".format(account_id, page))
    else:
        primary = InlineKeyboardButton(text=t("bot.button.start"), callback_data="start:{0}:{1}".format(account_id, page))

    rows = [[primary]]
    if snapshot.status in (SessionStatus.AWAITING_GUARD, SessionStatus.AWAITING_EMAIL):
        rows.append([InlineKeyboardButton(text=t("bot.button.cancel_login"), callback_data="cancel")])
    rows.extend(
        [
            [
                InlineKeyboardButton(text=t("bot.button.stats"), callback_data="stats:{0}:{1}".format(account_id, page)),
                InlineKeyboardButton(text=t("bot.button.edit"), callback_data="edit:{0}:{1}".format(account_id, page)),
            ],
            [InlineKeyboardButton(text=t("bot.button.delete"), callback_data="delete:{0}:{1}".format(account_id, page))],
            [InlineKeyboardButton(text=t("bot.button.all_accounts"), callback_data="home:{0}".format(page))],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def account_text(account: Account, stats: AccountStats, snapshot: SessionSnapshot, detailed: bool = False,
                 game_names: Optional[Dict[int, str]] = None) -> str:
    text = "<b>🎮 {0}</b>\n\n".format(html.escape(account.title))
    text += t("bot.account.login", username=html.escape(account.username))
    text += t("bot.account.status", status=status_label(snapshot))
    if snapshot.status == SessionStatus.RECONNECTING:
        text += t("bot.account.reconnect_attempt", attempt=snapshot.reconnect_attempt)
        if snapshot.down_since is not None:
            text += t("bot.account.reconnect_down", duration=format_outage(time.time() - snapshot.down_since))
        if snapshot.retry_at is not None and snapshot.retry_at > time.time():
            text += t("bot.account.reconnect_next", seconds=int(math.ceil(snapshot.retry_at - time.time())))
        text += "\n"
    text += t("bot.account.guard", mode=t("bot.guard.mode.auto" if account.shared_secret else "bot.guard.mode.manual"))
    text += t("bot.account.games_header")
    if account.custom_game_name:
        text += t("bot.account.custom_game", name=html.escape(account.custom_game_name))
    for game in account.games:
        name = (game_names or {}).get(game, t("bot.account.name_unavailable"))
        # Bound even a 50-game card in Telegram's UTF-16 message budget.
        if len(name.encode("utf-16-le")) > 64:
            name = name.encode("utf-16-le")[:60].decode("utf-16-le", errors="ignore") + "…"
        text += "• {0} — <code>{1}</code>\n".format(html.escape(name), game)
    text += "\n"
    text += t("bot.account.total", duration=format_duration(stats.total_seconds))

    if stats.is_active:
        text += t("bot.account.session_active", duration=format_duration(stats.current_session_seconds))
    else:
        text += t("bot.account.session_idle")

    if detailed:
        text += t("bot.account.completed", count=stats.completed_sessions)
        text += t("bot.account.stats_note")

    if snapshot.guard_type == "confirmation":
        text += t("bot.account.guard_confirmation")
    elif snapshot.guard_type == "mobile":
        text += t("bot.account.guard_mobile")
    elif snapshot.guard_type == "email":
        text += t("bot.account.guard_email")

    if snapshot.error:
        text += t("bot.account.state", error=html.escape(snapshot.error))
    return text


def edit_keyboard(account_id: int, page: int, has_custom_game: bool = False,
                  has_guard_secret: bool = False) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("bot.button.title"), callback_data="field:{0}:title:{1}".format(account_id, page))],
            [InlineKeyboardButton(text=t("bot.button.username"), callback_data="field:{0}:username:{1}".format(account_id, page))],
            [InlineKeyboardButton(text=t("bot.button.password"), callback_data="field:{0}:password:{1}".format(account_id, page))],
            [InlineKeyboardButton(text=t("bot.button.guard_secret"), callback_data="field:{0}:shared_secret:{1}".format(account_id, page))],
            *([[InlineKeyboardButton(text=t("bot.button.clear_secret"), callback_data="clear_secret:{0}:{1}".format(account_id, page))]] if has_guard_secret else []),
            [InlineKeyboardButton(text=t("bot.button.app_id"), callback_data="field:{0}:games:{1}".format(account_id, page))],
            [InlineKeyboardButton(text=t("bot.button.custom_game"), callback_data="field:{0}:custom_game_name:{1}".format(account_id, page))],
            *([[InlineKeyboardButton(text=t("bot.button.clear_custom"), callback_data="clear_custom:{0}:{1}".format(account_id, page))]] if has_custom_game else []),
            [InlineKeyboardButton(text=t("bot.button.back"), callback_data="account:{0}:{1}".format(account_id, page))],
        ]
    )


def form_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("bot.button.cancel"), callback_data="cancel")]]
    )


def delete_keyboard(account_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("bot.button.delete_confirm"), callback_data="confirm_delete:{0}:{1}".format(account_id, page))],
            [InlineKeyboardButton(text=t("bot.button.cancel_back"), callback_data="account:{0}:{1}".format(account_id, page))],
        ]
    )


class SingleMessageUI:
    """Keeps a single persistent bot message per chat and refreshes it in place."""

    def __init__(self, bot: Bot, database: Database) -> None:
        self._bot = bot
        self._database = database
        self._refresh_tasks: Dict[int, asyncio.Task] = {}
        self._screen_versions: Dict[int, int] = {}
        self._screen_context = ContextVar("screen_context", default=None)
        self._message_locks: Dict[int, asyncio.Lock] = {}

    async def navigation_middleware(self, handler, event, data):
        message = getattr(event, "message", None) or event
        if not hasattr(message, "chat") or getattr(event, "data", None) == "noop":
            return await handler(event, data)
        chat_id = int(message.chat.id)
        version = self._screen_versions.get(chat_id, 0) + 1
        self._screen_versions[chat_id] = version
        context = self._screen_context.set((chat_id, version))
        self.stop_live_refresh(chat_id)
        try:
            return await handler(event, data)
        finally:
            self._screen_context.reset(context)

    def is_current_screen(self, chat_id: int) -> bool:
        context = self._screen_context.get()
        return context is None or context == (int(chat_id), self._screen_versions.get(int(chat_id), 0))

    async def show_for_chat(
        self, chat_id: int, text: str, keyboard: InlineKeyboardMarkup
    ) -> None:
        async with self._message_locks.setdefault(int(chat_id), asyncio.Lock()):
            if not self.is_current_screen(chat_id):
                return
            # Finish an in-flight Telegram edit before allowing the next screen
            # to send its edit, even if its refresh task was just cancelled.
            update = asyncio.create_task(self._show_for_chat(chat_id, text, keyboard))
            try:
                await asyncio.shield(update)
            except asyncio.CancelledError:
                try:
                    await update
                finally:
                    raise

    async def _show_for_chat(
        self, chat_id: int, text: str, keyboard: InlineKeyboardMarkup
    ) -> None:
        message_id = self._database.get_control_message(chat_id)
        if message_id is not None:
            try:
                await self._bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
                return
            except TelegramBadRequest as error:
                if "message is not modified" in str(error).lower():
                    return
                logger.info(t("bot.log.control_message_unavailable", message_id=message_id, error=error))
            except TelegramForbiddenError:
                raise

        if not self.is_current_screen(chat_id):
            return
        message = await self._bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        self._database.set_control_message(chat_id, message.message_id)
        return

    async def adopt_and_show(
        self, message: Message, text: str, keyboard: InlineKeyboardMarkup
    ) -> None:
        self._database.set_control_message(message.chat.id, message.message_id)
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as error:
            if "message is not modified" not in str(error).lower():
                raise

    def start_live_refresh(
        self, chat_id: int, renderer: Callable[[], Awaitable[None]], interval: int = 2
    ) -> None:
        if not self.is_current_screen(chat_id):
            return
        self.stop_live_refresh(chat_id)
        self._refresh_tasks[int(chat_id)] = asyncio.create_task(
            self._refresh_loop(int(chat_id), renderer, max(2, int(interval)))
        )

    def stop_live_refresh(self, chat_id: int) -> None:
        if not self.is_current_screen(chat_id):
            return
        task = self._refresh_tasks.pop(int(chat_id), None)
        if task and task is not asyncio.current_task():
            task.cancel()

    async def _refresh_loop(
        self, chat_id: int, renderer: Callable[[], Awaitable[None]], interval: int
    ) -> None:
        failures = 0
        delay = interval
        try:
            while True:
                await asyncio.sleep(delay)
                if (not self.is_current_screen(chat_id)
                        or self._refresh_tasks.get(chat_id) is not asyncio.current_task()):
                    return
                try:
                    await renderer()
                except (TelegramNetworkError, TelegramServerError, TelegramRetryAfter) as error:
                    failures += 1
                    if isinstance(error, TelegramRetryAfter):
                        delay = max(interval, error.retry_after)
                    else:
                        delay = min(60, max(2, interval) * 2 ** min(failures - 1, 5))
                    logger.warning(
                        t("bot.log.refresh_failed", chat_id=chat_id, error=type(error).__name__,
                          delay=delay, attempt=failures)
                    )
                    continue
                if failures:
                    logger.info(t("bot.log.refresh_restored", chat_id=chat_id, failures=failures))
                failures = 0
                delay = interval
        except asyncio.CancelledError:
            raise
        except TelegramForbiddenError:
            logger.warning(t("bot.log.refresh_forbidden", chat_id=chat_id))
        except Exception:
            logger.exception(t("bot.log.live_refresh_failed", chat_id=chat_id))
        finally:
            if self._refresh_tasks.get(chat_id) is asyncio.current_task():
                self._refresh_tasks.pop(chat_id, None)
