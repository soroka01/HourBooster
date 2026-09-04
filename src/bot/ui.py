"""One-message Telegram UI primitives and screen builders."""

import asyncio
import html
import logging
from typing import Awaitable, Callable, Dict, Iterable, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

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
        return "{0}д {1:02d}:{2:02d}:{3:02d}".format(days, hours, minutes, seconds)
    return "{0:02d}:{1:02d}:{2:02d}".format(hours, minutes, seconds)


def status_label(snapshot: SessionSnapshot) -> str:
    labels = {
        SessionStatus.ACTIVE: "🟢 Буст идёт",
        SessionStatus.CONNECTING: "🟡 Подключение",
        SessionStatus.AWAITING_GUARD: "🔐 Нужен Steam Guard",
        SessionStatus.AWAITING_EMAIL: "📧 Нужен email-код",
        SessionStatus.STOPPING: "🟠 Остановка",
        SessionStatus.ERROR: "🔴 Ошибка",
        SessionStatus.STOPPED: "⚪ Остановлен",
        SessionStatus.IDLE: "⚪ Остановлен",
    }
    return labels.get(snapshot.status, "⚪ Неизвестно")


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

    rows.extend(
        [
            [InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="new")],
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="home:{0}".format(page)),
            ],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def dashboard_text(rows: Iterable[tuple], total_accounts: int) -> str:
    rows = list(rows)
    active = sum(1 for _, _, snapshot in rows if snapshot.status == SessionStatus.ACTIVE)
    total_seconds = sum(stats.total_seconds for _, stats, _ in rows)
    text = "<b>🎮 Steam Hour Booster</b>\n"
    text += "<i>Один экран для ваших Steam-сессий</i>\n\n"
    text += "👥 Аккаунтов: <b>{0}</b>  •  🟢 На странице активно: <b>{1}</b>\n".format(total_accounts, active)
    text += "⏱ На этой странице всего: <b>{0}</b>\n".format(format_duration(total_seconds))

    if not rows:
        text += "\n✨ Пока нет аккаунтов. Добавьте первый — логин и пароль останутся только в локальной SQLite-базе."
        return text

    text += "\n<b>Выберите аккаунт:</b>\n"
    for account, stats, snapshot in rows:
        text += "\n{0} <b>{1}</b>\n".format(status_label(snapshot).split(" ")[0], html.escape(account.title))
        text += "└ ⏱ {0}  •  🎯 игр: {1}\n".format(format_duration(stats.total_seconds), len(account.games))
    return text


def account_keyboard(account_id: int, snapshot: SessionSnapshot, page: int) -> InlineKeyboardMarkup:
    if snapshot.status in (SessionStatus.ACTIVE, SessionStatus.CONNECTING, SessionStatus.STOPPING):
        primary = InlineKeyboardButton(text="⏹️ Остановить", callback_data="stop:{0}:{1}".format(account_id, page))
    elif snapshot.status in (SessionStatus.AWAITING_GUARD, SessionStatus.AWAITING_EMAIL):
        primary = InlineKeyboardButton(text="🔐 Ввести код", callback_data="guard:{0}:{1}".format(account_id, page))
    else:
        primary = InlineKeyboardButton(text="🚀 Запустить", callback_data="start:{0}:{1}".format(account_id, page))

    rows = [[primary]]
    if snapshot.status in (SessionStatus.AWAITING_GUARD, SessionStatus.AWAITING_EMAIL):
        rows.append([InlineKeyboardButton(text="❌ Отменить вход", callback_data="cancel")])
    rows.extend(
        [
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="stats:{0}:{1}".format(account_id, page)),
                InlineKeyboardButton(text="✏️ Настроить", callback_data="edit:{0}:{1}".format(account_id, page)),
            ],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data="delete:{0}:{1}".format(account_id, page))],
            [InlineKeyboardButton(text="⬅️ Ко всем аккаунтам", callback_data="home:{0}".format(page))],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def account_text(account: Account, stats: AccountStats, snapshot: SessionSnapshot, detailed: bool = False,
                 game_names: Optional[Dict[int, str]] = None) -> str:
    text = "<b>🎮 {0}</b>\n\n".format(html.escape(account.title))
    text += "👤 Логин: <code>{0}</code>\n".format(html.escape(account.username))
    text += "📡 Статус: <b>{0}</b>\n".format(status_label(snapshot))
    text += "🎯 Игры:\n"
    for game in account.games:
        name = (game_names or {}).get(game, "Название недоступно")
        # Bound even a 50-game card in Telegram's UTF-16 message budget.
        if len(name.encode("utf-16-le")) > 64:
            name = name.encode("utf-16-le")[:60].decode("utf-16-le", errors="ignore") + "…"
        text += "• {0} — <code>{1}</code>\n".format(html.escape(name), game)
    text += "\n"
    text += "⏱ Всего буста: <b>{0}</b>\n".format(format_duration(stats.total_seconds))

    if stats.is_active:
        text += "🟢 Текущая сессия: <b>{0}</b>\n".format(format_duration(stats.current_session_seconds))
    else:
        text += "💤 Текущая сессия: <b>не запущена</b>\n"

    if detailed:
        text += "🔢 Завершённых сессий: <b>{0}</b>\n".format(stats.completed_sessions)
        text += "\n<i>Время начинает считаться только после успешного входа Steam.</i>"

    if snapshot.error:
        text += "\n\n⚠️ <b>Состояние:</b> {0}".format(html.escape(snapshot.error))
    return text


def edit_keyboard(account_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏷 Название", callback_data="field:{0}:title:{1}".format(account_id, page))],
            [InlineKeyboardButton(text="👤 Логин Steam", callback_data="field:{0}:username:{1}".format(account_id, page))],
            [InlineKeyboardButton(text="🔑 Пароль Steam", callback_data="field:{0}:password:{1}".format(account_id, page))],
            [InlineKeyboardButton(text="🎯 Steam App ID", callback_data="field:{0}:games:{1}".format(account_id, page))],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="account:{0}:{1}".format(account_id, page))],
        ]
    )


def form_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✖️ Отменить", callback_data="cancel")]]
    )


def delete_keyboard(account_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Да, удалить", callback_data="confirm_delete:{0}:{1}".format(account_id, page))],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="account:{0}:{1}".format(account_id, page))],
        ]
    )


class SingleMessageUI:
    """Keeps a single persistent bot message per chat and refreshes it in place."""

    def __init__(self, bot: Bot, database: Database) -> None:
        self._bot = bot
        self._database = database
        self._refresh_tasks: Dict[int, asyncio.Task] = {}

    async def show_for_chat(
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
                logger.info("Control message %s is unavailable: %s", message_id, error)
            except TelegramForbiddenError:
                raise

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
        self.stop_live_refresh(chat_id)
        self._refresh_tasks[int(chat_id)] = asyncio.create_task(
            self._refresh_loop(int(chat_id), renderer, max(2, int(interval)))
        )

    def stop_live_refresh(self, chat_id: int) -> None:
        task = self._refresh_tasks.pop(int(chat_id), None)
        if task:
            task.cancel()

    async def _refresh_loop(
        self, chat_id: int, renderer: Callable[[], Awaitable[None]], interval: int
    ) -> None:
        try:
            while True:
                await asyncio.sleep(interval)
                await renderer()
        except asyncio.CancelledError:
            raise
        except TelegramForbiddenError:
            logger.info("Chat %s is no longer available for live refresh", chat_id)
        except Exception:
            logger.exception("Live refresh failed for chat %s", chat_id)
        finally:
            self._refresh_tasks.pop(chat_id, None)
