"""Telegram controller for the dynamic, one-message Steam Hour Booster UI."""

import asyncio
import html
import logging
import time
from typing import Optional, Tuple

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..i18n import LANGUAGE_SETTING, other_language, set_language, t
from ..storage import Account, Database, StorageError, parse_game_ids
from ..steam.guard import (
    GuardSecretError, code_seconds_left, extract_shared_secret, generate_code, parse_mafile, steam_clock,
)
from ..steam.steam_manager import LIVE_STATUSES, SessionStatus, SteamSessionManager
from ..steam.game_names import GameNames
from .commands import set_bot_commands
from .states import AccountForm, GuardCode
from .ui import (
    PAGE_SIZE,
    SingleMessageUI,
    account_keyboard,
    account_text,
    code_keyboard,
    code_text,
    dashboard_keyboard,
    dashboard_text,
    delete_keyboard,
    edit_keyboard,
    form_keyboard,
    import_keyboard,
)

logger = logging.getLogger(__name__)

MAX_GUARD_FILE_BYTES = 64 * 1024
MAX_IMPORT_LINES = 15
CODE_VIEW_SECONDS = 300


class BoosterController:
    def __init__(self, bot: Bot, database: Database, sessions: SteamSessionManager) -> None:
        self.bot = bot
        self.database = database
        self.sessions = sessions
        self.ui = SingleMessageUI(bot, database)
        self.game_names = GameNames()
        self._import_lock = asyncio.Lock()
        self.router = Router(name="booster-controller")
        self.router.message.middleware(self.ui.navigation_middleware)
        self.router.callback_query.middleware(self.ui.navigation_middleware)
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.router.message.register(self.show_home_command, Command("start", "menu"))
        self.router.message.register(self.cancel_command, Command("cancel"))
        self.router.callback_query.register(self.handle_callback)

        self.router.message.register(self.add_title, AccountForm.add_title)
        self.router.message.register(self.add_username, AccountForm.add_username)
        self.router.message.register(self.add_password, AccountForm.add_password)
        self.router.message.register(self.add_games, AccountForm.add_games)
        self.router.message.register(self.edit_value, AccountForm.edit_value)
        self.router.message.register(self.import_mafiles, AccountForm.import_mafiles)
        self.router.message.register(self.guard_code, GuardCode.waiting)
        self.router.message.register(self.unknown_message, StateFilter(None))

    @staticmethod
    def _chat_id(event: Message) -> int:
        return int(event.chat.id)

    @staticmethod
    async def _delete_input(message: Message) -> None:
        try:
            await message.delete()
        except Exception:
            pass

    async def _download_text(self, message: Message) -> str:
        """Text of a small uploaded document, downloaded in memory; never logged or echoed."""
        document = message.document
        if document.file_size is not None and document.file_size > MAX_GUARD_FILE_BYTES:
            raise GuardSecretError(t("bot.error.file_too_large"))
        try:
            buffer = await self.bot.download(document)
        except TelegramAPIError:
            raise GuardSecretError(t("bot.error.download_failed")) from None
        raw = buffer.read() if buffer is not None else b""
        if len(raw) > MAX_GUARD_FILE_BYTES:
            raise GuardSecretError(t("bot.error.file_too_large"))
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _parse_callback(data: str, expected_parts: int) -> Optional[Tuple[str, ...]]:
        parts = tuple(data.split(":"))
        if len(parts) != expected_parts:
            return None
        return parts

    @staticmethod
    def _page(value: object) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    async def show_home_command(self, message: Message, state: FSMContext) -> None:
        await state.clear()
        await self.render_home(self._chat_id(message), 0, start_refresh=True)

    async def cancel_command(self, message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        await state.clear()
        account_id = self.sessions.cancel_pending(message.from_user.id, data.get("account_id"))
        await self._delete_input(message)
        if account_id:
            await self.render_account(self._chat_id(message), account_id, self._page(data.get("page")), True)
        else:
            await self.render_home(self._chat_id(message), self._page(data.get("page")), True)

    async def unknown_message(self, message: Message) -> None:
        await self.render_home(self._chat_id(message), 0, True)

    async def handle_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        if callback.message is None:
            return

        chat_id = callback.message.chat.id
        self.database.set_control_message(chat_id, callback.message.message_id)
        data = callback.data or ""

        if data == "noop":
            return
        if data == "new":
            await self.begin_add(chat_id, state)
            return
        if data == "import_guard":
            await self.begin_import(chat_id, state)
            return
        if data == "lang":
            await state.clear()
            await self.switch_language(chat_id)
            return
        if data == "cancel":
            form_data = await state.get_data()
            await state.clear()
            account_id = self.sessions.cancel_pending(callback.from_user.id, form_data.get("account_id"))
            if account_id:
                await self.render_account(chat_id, account_id, self._page(form_data.get("page")), True)
            else:
                await self.render_home(chat_id, self._page(form_data.get("page")), True)
            return
        if data.startswith("home:"):
            await state.clear()
            parts = self._parse_callback(data, 2)
            await self.render_home(chat_id, self._page(parts[1]) if parts else 0, True)
            return
        if data.startswith("account:"):
            parts = self._parse_callback(data, 2) or self._parse_callback(data, 3)
            if not parts:
                await self.render_home(chat_id, 0, True)
                return
            try:
                account_id = int(parts[1])
            except ValueError:
                await self.render_home(chat_id, 0, True)
                return
            page = self._page(parts[2]) if len(parts) == 3 else 0
            await state.clear()
            await self.render_account(chat_id, account_id, page, True)
            return
        if data.startswith("start:"):
            parts = self._parse_callback(data, 2) or self._parse_callback(data, 3)
            if parts:
                await self.start_account(chat_id, callback.from_user.id, int(parts[1]), self._page(parts[2]) if len(parts) == 3 else 0, state)
            return
        if data.startswith("guard:"):
            parts = self._parse_callback(data, 2) or self._parse_callback(data, 3)
            if parts:
                await self.prompt_guard(chat_id, int(parts[1]), self._page(parts[2]) if len(parts) == 3 else 0, state)
            return
        if data.startswith("stop:"):
            parts = self._parse_callback(data, 2) or self._parse_callback(data, 3)
            if parts:
                await self.stop_account(chat_id, int(parts[1]), self._page(parts[2]) if len(parts) == 3 else 0)
            return
        if data.startswith("stats:"):
            parts = self._parse_callback(data, 2) or self._parse_callback(data, 3)
            if parts:
                await self.render_account(chat_id, int(parts[1]), self._page(parts[2]) if len(parts) == 3 else 0, True, detailed=True)
            return
        if data.startswith("code:"):
            parts = self._parse_callback(data, 3)
            if parts:
                await state.clear()
                await self.render_code(chat_id, int(parts[1]), self._page(parts[2]), True)
            return
        if data.startswith("edit:"):
            parts = self._parse_callback(data, 2) or self._parse_callback(data, 3)
            if parts:
                await self.show_edit_menu(chat_id, int(parts[1]), self._page(parts[2]) if len(parts) == 3 else 0, state)
            return
        if data.startswith("field:"):
            parts = self._parse_callback(data, 3) or self._parse_callback(data, 4)
            if parts:
                await self.begin_edit_field(chat_id, int(parts[1]), parts[2], self._page(parts[3]) if len(parts) == 4 else 0, state)
            return
        if data.startswith("clear_custom:"):
            parts = self._parse_callback(data, 3)
            if parts:
                account_id, page = int(parts[1]), self._page(parts[2])
                if self.sessions.has_live_session(account_id):
                    await self.render_account(chat_id, account_id, page, True)
                    return
                if self.database.get_account(account_id):
                    self.database.update_account(account_id, "custom_game_name", "")
                await self.show_edit_menu(chat_id, account_id, page, state)
            return
        if data.startswith("clear_secret:"):
            parts = self._parse_callback(data, 3)
            if parts:
                account_id, page = int(parts[1]), self._page(parts[2])
                if self.sessions.has_live_session(account_id):
                    await self.render_account(chat_id, account_id, page, True)
                    return
                if self.database.get_account(account_id):
                    self.database.update_account(account_id, "shared_secret", "")
                await self.show_edit_menu(chat_id, account_id, page, state)
            return
        if data.startswith("delete:"):
            parts = self._parse_callback(data, 2) or self._parse_callback(data, 3)
            if parts:
                await self.confirm_delete(chat_id, int(parts[1]), self._page(parts[2]) if len(parts) == 3 else 0)
            return
        if data.startswith("confirm_delete:"):
            parts = self._parse_callback(data, 3)
            if parts:
                await self.delete_account(chat_id, int(parts[1]), self._page(parts[2]), state)
            return

        await self.render_home(chat_id, 0, True)

    async def switch_language(self, chat_id: int) -> None:
        new_language = other_language()
        self.database.set_settings({LANGUAGE_SETTING: new_language})
        set_language(new_language)
        try:
            await set_bot_commands(self.bot)
        except TelegramAPIError as error:
            logger.warning(t("bot.log.language_commands_failed", error=type(error).__name__))
        await self.render_home(chat_id, 0, True)

    async def render_home(self, chat_id: int, page: int, start_refresh: bool) -> None:
        _, total = self.database.list_accounts(0, PAGE_SIZE)
        max_page = max(0, (total - 1) // PAGE_SIZE)
        page = min(max(0, page), max_page)
        accounts, total = self.database.list_accounts(page, PAGE_SIZE)
        rows = []
        has_live = False
        for account in accounts:
            stats = self.database.get_account_stats(account.id)
            snapshot = self.sessions.get_snapshot(account.id)
            has_live = has_live or snapshot.status in LIVE_STATUSES
            rows.append((account, stats, snapshot))

        await self.ui.show_for_chat(
            chat_id,
            dashboard_text(rows, total),
            dashboard_keyboard(accounts, page, total),
        )
        if start_refresh and has_live:
            self.ui.start_live_refresh(
                chat_id,
                lambda: self.render_home(chat_id, page, False),
                interval=2,
            )
        elif not has_live:
            self.ui.stop_live_refresh(chat_id)

    async def render_account(
        self, chat_id: int, account_id: int, page: int, start_refresh: bool, detailed: bool = False
    ) -> None:
        account = self.database.get_account(account_id)
        if account is None:
            await self.render_home(chat_id, page, True)
            return

        names = await self.game_names.get_names(account.games)
        if not self.ui.is_current_screen(chat_id):
            return
        stats = self.database.get_account_stats(account.id)
        snapshot = self.sessions.get_snapshot(account.id)
        await self.ui.show_for_chat(
            chat_id,
            account_text(account, stats, snapshot, detailed=detailed, game_names=names),
            account_keyboard(account.id, snapshot, page, bool(account.shared_secret)),
        )
        if start_refresh and snapshot.status in LIVE_STATUSES:
            self.ui.start_live_refresh(
                chat_id,
                lambda: self.render_account(chat_id, account.id, page, False, detailed),
                interval=2,
            )
        elif snapshot.status not in LIVE_STATUSES:
            self.ui.stop_live_refresh(chat_id)

    async def render_code(
        self, chat_id: int, account_id: int, page: int, start_refresh: bool, opened_at: Optional[float] = None
    ) -> None:
        """The current Guard code for the owner; refreshes itself for a few minutes, then hides the code."""
        account = self.database.get_account(account_id)
        if account is None or not account.shared_secret:
            await self.render_account(chat_id, account_id, page, True)
            return

        opened_at = time.monotonic() if opened_at is None else opened_at
        expired = time.monotonic() - opened_at >= CODE_VIEW_SECONDS
        code, seconds_left = None, 0
        if not expired:
            # Steam's clock is fetched over the network at most once an hour; keep that off the event loop.
            moment = await asyncio.to_thread(steam_clock.now)
            if not self.ui.is_current_screen(chat_id):
                return
            code = generate_code(account.shared_secret, moment)
            seconds_left = code_seconds_left(moment)
        await self.ui.show_for_chat(
            chat_id,
            code_text(account.title, code, seconds_left),
            code_keyboard(account_id, page, expired),
        )
        if expired:
            self.ui.stop_live_refresh(chat_id)
        elif start_refresh:
            self.ui.start_live_refresh(
                chat_id,
                lambda: self.render_code(chat_id, account_id, page, False, opened_at),
                interval=2,
            )

    async def begin_add(self, chat_id: int, state: FSMContext) -> None:
        self.ui.stop_live_refresh(chat_id)
        await state.clear()
        await state.set_state(AccountForm.add_title)
        await state.update_data(page=0)
        await self.ui.show_for_chat(
            chat_id,
            t("bot.add.title"),
            form_keyboard(),
        )

    async def add_title(self, message: Message, state: FSMContext) -> None:
        title = (message.text or "").strip()
        await self._delete_input(message)
        if not title or len(title) > 48:
            await self.ui.show_for_chat(
                self._chat_id(message),
                t("bot.add.title_invalid"),
                form_keyboard(),
            )
            return
        await state.update_data(title=title)
        await state.set_state(AccountForm.add_username)
        await self.ui.show_for_chat(
            self._chat_id(message),
            t("bot.add.username"),
            form_keyboard(),
        )

    async def add_username(self, message: Message, state: FSMContext) -> None:
        username = (message.text or "").strip()
        await self._delete_input(message)
        if not username or len(username) > 128:
            await self.ui.show_for_chat(
                self._chat_id(message),
                t("bot.add.username_invalid"),
                form_keyboard(),
            )
            return
        await state.update_data(username=username)
        await state.set_state(AccountForm.add_password)
        await self.ui.show_for_chat(
            self._chat_id(message),
            t("bot.add.password"),
            form_keyboard(),
        )

    async def add_password(self, message: Message, state: FSMContext) -> None:
        password = message.text or ""
        await self._delete_input(message)
        if not password or len(password) > 512:
            await self.ui.show_for_chat(
                self._chat_id(message),
                t("bot.add.password_invalid"),
                form_keyboard(),
            )
            return
        await state.update_data(password=password)
        await state.set_state(AccountForm.add_games)
        await self.ui.show_for_chat(
            self._chat_id(message),
            t("bot.add.games"),
            form_keyboard(),
        )

    async def add_games(self, message: Message, state: FSMContext) -> None:
        raw_games = message.text or ""
        await self._delete_input(message)
        try:
            games = parse_game_ids(raw_games)
            data = await state.get_data()
            account = self.database.create_account(
                str(data["title"]), str(data["username"]), str(data["password"]), games
            )
        except (KeyError, StorageError) as error:
            await self.ui.show_for_chat(
                self._chat_id(message),
                t("bot.add.games_error", error=html.escape(str(error))),
                form_keyboard(),
            )
            return

        await state.clear()
        await self.render_account(self._chat_id(message), account.id, 0, True)

    async def begin_import(self, chat_id: int, state: FSMContext) -> None:
        self.ui.stop_live_refresh(chat_id)
        await state.clear()
        if not self.database.list_accounts(0, 1)[1]:
            await self.render_home(chat_id, 0, True)
            return
        await state.set_state(AccountForm.import_mafiles)
        await state.update_data(page=0, import_lines=[])
        await self._render_import(chat_id, [])

    async def _render_import(self, chat_id: int, lines: list, hint: str = "") -> None:
        text = t("bot.import.text")
        if lines:
            text += "\n\n" + t("bot.import.results_header") + "\n" + "\n".join(lines)
        if hint:
            text += "\n\n" + hint
        await self.ui.show_for_chat(chat_id, text, import_keyboard())

    async def _import_one(self, message: Message) -> list:
        try:
            mafile = parse_mafile(await self._download_text(message))
        except GuardSecretError as error:
            name = html.escape((message.document.file_name or t("bot.import.file_default"))[:40])
            return [t("bot.import.unreadable", name=name, error=html.escape(str(error)))]
        accounts = self.database.find_accounts_by_username(mafile.account_name)
        if not accounts:
            return [t("bot.import.no_account", username=html.escape(mafile.account_name[:64]))]
        results = []
        for account in accounts:
            try:
                self.database.update_account(account.id, "shared_secret", mafile.shared_secret)
            except (ValueError, StorageError) as error:
                results.append("⚠️ {0}: {1}".format(html.escape(account.title), html.escape(str(error))))
            else:
                results.append("✅ {0}".format(html.escape(account.title)))
        return results

    async def import_mafiles(self, message: Message, state: FSMContext) -> None:
        await self._delete_input(message)
        chat_id = self._chat_id(message)
        # Albums arrive as separate messages; serialize them so the result list stays complete.
        async with self._import_lock:
            if await state.get_state() != AccountForm.import_mafiles.state:
                return
            data = await state.get_data()
            lines = list(data.get("import_lines") or [])
            hint = ""
            if message.document is None:
                hint = t("bot.import.document_required")
            else:
                lines.extend(await self._import_one(message))
                lines = lines[-MAX_IMPORT_LINES:]
                await state.update_data(import_lines=lines)
            await self._render_import(chat_id, lines, hint)

    async def show_edit_menu(self, chat_id: int, account_id: int, page: int, state: FSMContext) -> None:
        account = self.database.get_account(account_id)
        if account is None:
            await self.render_home(chat_id, page, True)
            return
        if self.sessions.has_live_session(account_id):
            await self.render_account(chat_id, account_id, page, True)
            return

        self.ui.stop_live_refresh(chat_id)
        await state.clear()
        text = t(
            "bot.edit.menu",
            title=html.escape(account.title),
            guard=t("bot.guard.mode.auto_saved" if account.shared_secret else "bot.guard.mode.manual"),
        )
        await self.ui.show_for_chat(
            chat_id,
            text,
            edit_keyboard(account_id, page, bool(account.custom_game_name), bool(account.shared_secret)),
        )

    async def begin_edit_field(
        self, chat_id: int, account_id: int, field: str, page: int, state: FSMContext
    ) -> None:
        account = self.database.get_account(account_id)
        prompt_fields = ("title", "username", "password", "games", "shared_secret", "custom_game_name")
        if account is None or field not in prompt_fields:
            await self.render_home(chat_id, page, True)
            return
        if self.sessions.has_live_session(account_id):
            await self.render_account(chat_id, account_id, page, True)
            return
        await state.clear()
        await state.set_state(AccountForm.edit_value)
        await state.update_data(account_id=account_id, field=field, page=page)
        await self.ui.show_for_chat(
            chat_id,
            t("bot.edit.field", title=html.escape(account.title), prompt=t("bot.edit.prompt." + field)),
            form_keyboard(),
        )

    async def edit_value(self, message: Message, state: FSMContext) -> None:
        value = message.text or ""
        await self._delete_input(message)
        data = await state.get_data()
        try:
            account_id = int(data["account_id"])
            field = str(data["field"])
            page = self._page(data.get("page"))
            if self.sessions.has_live_session(account_id):
                await state.clear()
                await self.render_account(self._chat_id(message), account_id, page, True)
                return
            if field == "custom_game_name" and not str(value).strip():
                raise StorageError(t("bot.error.custom_game_empty"))
            if field == "games":
                value = parse_game_ids(value)
            if field == "shared_secret":
                text = await self._download_text(message) if message.document else value
                body = text.strip().lstrip("\ufeff")
                if body.startswith("{"):
                    mafile = parse_mafile(body)
                    account = self.database.get_account(account_id)
                    if account is not None and mafile.account_name.casefold() != account.username.casefold():
                        raise GuardSecretError(t("bot.error.mafile_other_login"))
                    value = mafile.shared_secret
                else:
                    value = extract_shared_secret(text)
            self.database.update_account(account_id, field, value)
            if field in ("password", "username"):
                self.sessions.forget_account(account_id)
        except (KeyError, ValueError, StorageError) as error:
            await self.ui.show_for_chat(
                self._chat_id(message),
                t("bot.edit.error", error=html.escape(str(error))),
                form_keyboard(),
            )
            return

        await state.clear()
        await self.render_account(self._chat_id(message), account_id, page, True)

    async def start_account(self, chat_id: int, user_id: int, account_id: int, page: int, state: FSMContext) -> None:
        account = self.database.get_account(account_id)
        if account is None:
            await self.render_home(chat_id, 0, True)
            return
        await state.clear()
        self.sessions.start(account, user_id)
        await self.render_account(chat_id, account_id, page, True)
        await self._wait_for_login(chat_id, account_id, user_id, page, state)

    async def _wait_for_login(self, chat_id: int, account_id: int, user_id: int, page: int, state: FSMContext) -> None:
        for _ in range(12):
            if not self.ui.is_current_screen(chat_id):
                return
            snapshot = self.sessions.get_snapshot(account_id)
            if snapshot.status != SessionStatus.CONNECTING:
                break
            await asyncio.sleep(0.5)

        if not self.ui.is_current_screen(chat_id):
            return
        snapshot = self.sessions.get_snapshot(account_id)
        if snapshot.status in (SessionStatus.AWAITING_GUARD, SessionStatus.AWAITING_EMAIL):
            await state.set_state(GuardCode.waiting)
            await state.update_data(account_id=account_id, page=page)
        else:
            await state.clear()
        await self.render_account(chat_id, account_id, page, True)

    async def prompt_guard(self, chat_id: int, account_id: int, page: int, state: FSMContext) -> None:
        snapshot = self.sessions.get_snapshot(account_id)
        if snapshot.status in (SessionStatus.AWAITING_GUARD, SessionStatus.AWAITING_EMAIL):
            await state.set_state(GuardCode.waiting)
            await state.update_data(account_id=account_id, page=page)
        else:
            await state.clear()
        await self.render_account(chat_id, account_id, page, True)

    async def guard_code(self, message: Message, state: FSMContext) -> None:
        code = (message.text or "").strip()
        await self._delete_input(message)
        data = await state.get_data()
        if not code:
            await self.ui.show_for_chat(
                self._chat_id(message), t("bot.guard.empty"), form_keyboard()
            )
            return

        snapshot = self.sessions.submit_guard_code(message.from_user.id, code, data.get("account_id"))
        if snapshot is None:
            await state.clear()
            if data.get("account_id"):
                await self.render_account(self._chat_id(message), int(data["account_id"]), self._page(data.get("page")), True)
            else:
                await self.render_home(self._chat_id(message), self._page(data.get("page")), True)
            return

        await self.ui.show_for_chat(
            self._chat_id(message),
            t("bot.guard.checking"),
            form_keyboard(),
        )
        await self._wait_for_login(self._chat_id(message), snapshot.account_id, message.from_user.id, self._page(data.get("page")), state)

    async def stop_account(self, chat_id: int, account_id: int, page: int) -> None:
        loop = asyncio.get_running_loop()
        stopped = await loop.run_in_executor(None, self.sessions.stop, account_id)
        if not stopped:
            await self.render_account(chat_id, account_id, page, True)
            return
        await self.render_account(chat_id, account_id, page, True)

    async def confirm_delete(self, chat_id: int, account_id: int, page: int) -> None:
        account = self.database.get_account(account_id)
        if account is None:
            await self.render_home(chat_id, page, True)
            return
        if self.sessions.has_live_session(account_id):
            await self.render_account(chat_id, account_id, page, True)
            return
        self.ui.stop_live_refresh(chat_id)
        text = t("bot.delete.confirm", title=html.escape(account.title))
        await self.ui.show_for_chat(chat_id, text, delete_keyboard(account_id, page))

    async def delete_account(self, chat_id: int, account_id: int, page: int, state: FSMContext) -> None:
        if self.sessions.has_live_session(account_id):
            await self.render_account(chat_id, account_id, page, True)
            return
        self.database.delete_account(account_id)
        self.sessions.forget_account(account_id)
        await state.clear()
        await self.render_home(chat_id, page, True)
