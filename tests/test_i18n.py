import asyncio
import os
import re
import string
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from aiogram.types import InlineKeyboardMarkup

from src import i18n
from src.i18n import Text
from src.bot import ui
from src.bot.controller import BoosterController
from src.steam import game_names
from src.steam.auth import AuthError
from src.steam.steam_manager import SessionSnapshot, SessionStatus, SteamSessionManager, _Session, _message
from src.storage import Account, AccountStats, Database

CYR = re.compile("[Ѐ-ӿ]")
TAG = re.compile(r"<[^>]+>")


def keyboard_texts(markup: InlineKeyboardMarkup):
    return [button.text for row in markup.inline_keyboard for button in row]


class LanguageCase(unittest.TestCase):
    def setUp(self):
        self.addCleanup(i18n.set_language, os.environ.get("TEST_LANG", "en"))


class HelperTests(LanguageCase):
    def test_default_is_english_and_unknown_values_fall_back(self):
        self.assertEqual(i18n.DEFAULT_LANGUAGE, "en")
        for value in (None, "", "de", "  "):
            self.assertEqual(i18n.set_language(value), "en")

    def test_aliases_are_accepted(self):
        for value in ("ru", "RU", " Russian ", "rus"):
            self.assertEqual(i18n.normalize_language(value), "ru")
        for value in ("EN", "english"):
            self.assertEqual(i18n.normalize_language(value), "en")

    def test_other_language(self):
        i18n.set_language("en")
        self.assertEqual(i18n.other_language(), "ru")
        i18n.set_language("ru")
        self.assertEqual(i18n.other_language(), "en")

    def test_missing_key_returns_the_key_and_missing_translation_falls_back_to_english(self):
        i18n.set_language("ru")
        self.assertEqual(i18n.t("no.such.key"), "no.such.key")
        with mock.patch.dict(i18n.CATALOGS["en"], {"test.only_en": "only {x}"}):
            self.assertEqual(i18n.t("test.only_en", x=1), "only 1")

    def test_catalogs_have_the_same_keys_placeholders_and_tags(self):
        en, ru = i18n.CATALOGS["en"], i18n.CATALOGS["ru"]
        self.assertEqual(set(en), set(ru))
        for key in en:
            fields = lambda text: sorted(n for _, n, _, _ in string.Formatter().parse(text) if n is not None)
            self.assertEqual(fields(en[key]), fields(ru[key]), key)
            self.assertEqual(sorted(TAG.findall(en[key])), sorted(TAG.findall(ru[key])), key)
            if ".language.name." not in key:
                self.assertIsNone(CYR.search(en[key]), key)

    def test_every_text_formats_with_dummy_values(self):
        for language in i18n.LANGUAGES:
            i18n.set_language(language)
            for key, text in i18n.CATALOGS[language].items():
                names = {n for _, n, _, _ in string.Formatter().parse(text) if n}
                params = {n: 7 for n in names}
                i18n.t(key, **params)  # must not raise


class LazyTextTests(LanguageCase):
    def test_text_is_resolved_when_displayed(self):
        i18n.set_language("en")
        message = Text("steam.auth.bad_code")
        english = str(message)
        i18n.set_language("ru")
        self.assertNotEqual(str(message), english)
        self.assertEqual(str(message), i18n.t("steam.auth.bad_code"))

    def test_text_works_as_a_format_parameter_and_in_exceptions(self):
        i18n.set_language("en")
        error = AuthError(Text("steam.auth.bad_code"), 88)
        self.assertIs(_message(error).__class__, Text)
        nested = Text("steam.session.no_connection", reason=_message(error))
        english = str(nested)
        self.assertIn(str(error), english)
        i18n.set_language("ru")
        self.assertNotEqual(str(nested), english)
        self.assertEqual(str(error), i18n.t("steam.auth.bad_code"))

    def test_stored_session_errors_follow_a_language_switch(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Database(Path(temp) / "t.sqlite3")
            try:
                account = database.create_account("Main", "login", "pw", [730])
                manager = SteamSessionManager(database)
                manager._sessions[account.id] = _Session(
                    account=account, status=SessionStatus.ERROR, error=Text("steam.session.too_many_logins"))
                i18n.set_language("en")
                english = manager.get_snapshot(account.id).error
                self.assertIsNone(CYR.search(english))
                i18n.set_language("ru")
                self.assertIsNotNone(CYR.search(manager.get_snapshot(account.id).error))
            finally:
                database.close()

    def test_retry_reasons_end_with_a_period_in_both_languages(self):
        # steam.session.no_connection appends " Retrying." after the reason, so reasons must be sentences.
        for language in i18n.LANGUAGES:
            for key, text in i18n.CATALOGS[language].items():
                if key.startswith("steam.retry.") or key.startswith("steam.auth."):
                    self.assertTrue(text.rstrip().endswith("."), "{0} ({1})".format(key, language))

    def test_cyrillic_language_names_are_understood(self):
        self.assertEqual(i18n.normalize_language("Русский"), "ru")
        self.assertEqual(i18n.normalize_language("английский"), "en")


class RenderTests(LanguageCase):
    def account(self, secret=""):
        return Account(1, "Main <b>", "login", "pw", (730, 570), 3600, None, 1, 1, "My game", secret)

    def stats(self, active=False):
        return AccountStats(1, 3600, 120 if active else 0, 2, active)

    def snapshots(self):
        statuses = [SessionStatus.IDLE, SessionStatus.CONNECTING, SessionStatus.RECONNECTING, SessionStatus.AWAITING_GUARD,
                    SessionStatus.AWAITING_EMAIL, SessionStatus.ACTIVE, SessionStatus.STOPPING, SessionStatus.STOPPED,
                    SessionStatus.ERROR, SessionStatus.PAUSED, "weird"]
        for status in statuses:
            for guard in ("", "mobile", "email", "confirmation"):
                yield SessionSnapshot(1, status, "error text", guard, True, 3, 1000.0, 2000.0)

    def render_all(self):
        out = []
        for secret in ("", "AAAA"):
            account = self.account(secret)
            for snap in self.snapshots():
                for detailed in (False, True):
                    out.append(ui.account_text(account, self.stats(True), snap, detailed=detailed, game_names={730: "Dota 2"}))
                out += keyboard_texts(ui.account_keyboard(1, snap, 0))
                out.append(ui.status_label(snap))
            out += keyboard_texts(ui.edit_keyboard(1, 0, True, bool(secret)))
            out.append(ui.dashboard_text([(account, self.stats(), s) for s in self.snapshots()], 3))
        out += keyboard_texts(ui.dashboard_keyboard([self.account()], 0, 9))
        out += keyboard_texts(ui.import_keyboard()) + keyboard_texts(ui.form_keyboard()) + keyboard_texts(ui.delete_keyboard(1, 0))
        out += [ui.format_duration(100000), ui.format_outage(75), ui.format_outage(4000)]
        return out

    def test_english_ui_has_no_cyrillic_except_the_language_name(self):
        i18n.set_language("en")
        for text in self.render_all():
            self.assertIsNone(CYR.search(text.replace("Русский", "")), text)

    def test_russian_ui_is_russian(self):
        i18n.set_language("ru")
        joined = "\n".join(self.render_all())
        self.assertIn("Буст идёт", joined)
        self.assertIn("Переподключение", joined)
        self.assertIn("🛡 Steam Guard: <b>авто</b>", joined)
        self.assertIn("English", joined)  # the toggle offers the other language

    def test_status_labels_start_with_an_emoji_and_a_space_in_both_languages(self):
        # the dashboard shows only the part before the first space
        for language in i18n.LANGUAGES:
            i18n.set_language(language)
            for snap in self.snapshots():
                label = ui.status_label(snap)
                head, _, rest = label.partition(" ")
                self.assertTrue(rest and not head.isascii(), label)

    def test_language_button_offers_the_other_language(self):
        i18n.set_language("en")
        self.assertIn("🌐 Русский", keyboard_texts(ui.dashboard_keyboard([], 0, 0)))
        i18n.set_language("ru")
        self.assertIn("🌐 English", keyboard_texts(ui.dashboard_keyboard([], 0, 0)))


class GameNamesLanguageTests(LanguageCase):
    def test_store_language_follows_the_interface_and_cache_is_per_language(self):
        calls = []

        class Response:
            def __init__(self, params):
                self.params = params

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            def raise_for_status(self):
                pass

            async def json(self):
                app_id = self.params["appids"]
                return {app_id: {"success": True, "data": {"name": "{0} {1}".format(self.params["l"], app_id)}}}

        class Session:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            def get(self, url, params):
                calls.append(params["l"])
                return Response(params)

        async def scenario():
            names = game_names.GameNames()
            i18n.set_language("en")
            first = await names.get_names([730])
            i18n.set_language("ru")
            second = await names.get_names([730])
            i18n.set_language("en")
            third = await names.get_names([730])
            return first, second, third

        with mock.patch.object(game_names.aiohttp, "ClientSession", Session):
            first, second, third = asyncio.run(scenario())
        self.assertEqual(first, {730: "english 730"})
        self.assertEqual(second, {730: "russian 730"})
        self.assertEqual(third, first)
        self.assertEqual(calls, ["english", "russian"])  # switching back used the cache


class ToggleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Database(Path(self.temp.name) / "t.sqlite3")
        self.addCleanup(self.database.close)
        self.addCleanup(i18n.set_language, os.environ.get("TEST_LANG", "en"))
        i18n.set_language("en")
        self.bot = mock.AsyncMock()
        self.bot.send_message.return_value = types.SimpleNamespace(message_id=5)
        self.database.set_control_message(1, 5)
        self.controller = BoosterController(self.bot, self.database, SteamSessionManager(self.database))

    def last_screen(self):
        call = self.bot.edit_message_text.call_args
        return call.kwargs["text"], keyboard_texts(call.kwargs["reply_markup"])

    async def test_toggle_switches_language_saves_it_and_refreshes_everything(self):
        await self.controller.switch_language(1)
        self.assertEqual(i18n.get_language(), "ru")
        self.assertEqual(self.database.get_setting(i18n.LANGUAGE_SETTING), "ru")
        commands = self.bot.set_my_commands.call_args.args[0]
        self.assertTrue(all(CYR.search(c.description) for c in commands))
        text, buttons = self.last_screen()
        self.assertIn("Steam Hour Booster", text)
        self.assertIsNotNone(CYR.search(text))
        self.assertIn("🌐 English", buttons)

        await self.controller.switch_language(1)
        self.assertEqual(i18n.get_language(), "en")
        self.assertEqual(self.database.get_setting(i18n.LANGUAGE_SETTING), "en")
        commands = self.bot.set_my_commands.call_args.args[0]
        self.assertTrue(all(CYR.search(c.description) is None for c in commands))
        text, buttons = self.last_screen()
        self.assertIsNone(CYR.search(text))
        self.assertIn("🌐 Русский", buttons)

    async def test_edit_prompt_escapes_the_account_title(self):
        account = self.database.create_account("CS & <Dota>", "login", "pw", [730])
        state = mock.AsyncMock()
        await self.controller.begin_edit_field(1, account.id, "title", 0, state)
        text, _ = self.last_screen()
        self.assertIn("CS &amp; &lt;Dota&gt;", text)
        self.assertNotIn("<Dota>", text)

    async def test_toggle_survives_a_failing_command_menu_update(self):
        from aiogram.exceptions import TelegramNetworkError
        self.bot.set_my_commands.side_effect = TelegramNetworkError(method=mock.Mock(), message="down")
        await self.controller.switch_language(1)
        self.assertEqual(i18n.get_language(), "ru")
        self.assertEqual(self.database.get_setting(i18n.LANGUAGE_SETTING), "ru")


if __name__ == "__main__":
    unittest.main()
