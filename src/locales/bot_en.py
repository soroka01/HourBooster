"""Telegram bot messages (English)."""

MESSAGES = {
    # Command menu
    "bot.command.start": "🎮 Open accounts",
    "bot.command.menu": "🏠 Main menu",
    "bot.command.cancel": "✖️ Cancel input",
    # Language toggle
    "bot.language.name.en": "English",
    "bot.language.name.ru": "Русский",
    "bot.button.language": "🌐 {name}",
    # Access middleware
    "bot.access.denied_callback": "🚫 This bot is for its owner only.",
    "bot.access.denied_message": "🚫 This bot is set up for personal use by its owner.",
    # Durations and statuses
    "bot.duration.days_clock": "{days}d {hours:02d}:{minutes:02d}:{seconds:02d}",
    "bot.status.active": "🟢 Boosting",
    "bot.status.paused": "⏸️ Game interrupted",
    "bot.status.connecting": "🟡 Connecting",
    "bot.status.reconnecting": "🔄 Reconnecting",
    "bot.status.awaiting_guard": "🔐 Steam Guard needed",
    "bot.status.awaiting_email": "📧 Email code needed",
    "bot.status.stopping": "🟠 Stopping",
    "bot.status.error": "🔴 Error",
    "bot.status.stopped": "⚪ Stopped",
    "bot.status.unknown": "⚪ Unknown",
    # Buttons
    "bot.button.add_account": "➕ Add account",
    "bot.button.import_guard": "🛡 Import Guard (maFile)",
    "bot.button.refresh": "🔄 Refresh",
    "bot.button.done": "✅ Done",
    "bot.button.cancel": "✖️ Cancel",
    "bot.button.stop": "⏹️ Stop",
    "bot.button.enter_code": "🔐 Enter code",
    "bot.button.start": "🚀 Start",
    "bot.button.cancel_login": "❌ Cancel login",
    "bot.button.stats": "📊 Statistics",
    "bot.button.edit": "✏️ Settings",
    "bot.button.delete": "🗑 Delete",
    "bot.button.all_accounts": "⬅️ All accounts",
    "bot.button.title": "🏷 Name",
    "bot.button.username": "👤 Steam login",
    "bot.button.password": "🔑 Steam password",
    "bot.button.guard_secret": "🛡 Steam Guard secret",
    "bot.button.clear_secret": "✖️ Remove Guard secret",
    "bot.button.app_id": "🎯 Steam App ID",
    "bot.button.custom_game": "🎮 Custom game",
    "bot.button.clear_custom": "✖️ Remove custom game",
    "bot.button.back": "⬅️ Back",
    "bot.button.delete_confirm": "🗑 Yes, delete",
    "bot.button.cancel_back": "⬅️ Cancel",
    # Dashboard
    "bot.dashboard.header": "<b>🎮 Steam Hour Booster</b>\n<i>One screen for all your Steam sessions</i>\n\n",
    "bot.dashboard.counts": "👥 Accounts: <b>{total}</b>  •  🟢 Active on this page: <b>{active}</b>\n",
    "bot.dashboard.time": "⏱ Total on this page: <b>{duration}</b>\n",
    "bot.dashboard.empty": "\n✨ No accounts yet. Add your first one — the login and password stay only in the local SQLite database.",
    "bot.dashboard.choose": "\n<b>Choose an account:</b>\n",
    "bot.dashboard.row_stats": "└ ⏱ {duration}  •  🎯 games: {games}\n",
    # Account card
    "bot.account.login": "👤 Login: <code>{username}</code>\n",
    "bot.account.status": "📡 Status: <b>{status}</b>\n",
    "bot.account.reconnect_attempt": "🔄 No connection to Steam: attempt {attempt}",
    "bot.account.reconnect_down": ", down for {duration}",
    "bot.account.reconnect_next": " · next one in {seconds} s",
    "bot.account.guard": "🛡 Steam Guard: <b>{mode}</b>\n",
    "bot.account.games_header": "🎯 Games:\n",
    "bot.account.custom_game": "• <b>{name}</b> <i>(third-party game)</i>\n",
    "bot.account.name_unavailable": "Name unavailable",
    "bot.account.total": "⏱ Total boost time: <b>{duration}</b>\n",
    "bot.account.session_active": "🟢 Current session: <b>{duration}</b>\n",
    "bot.account.session_idle": "💤 Current session: <b>not running</b>\n",
    "bot.account.completed": "🔢 Completed sessions: <b>{count}</b>\n",
    "bot.account.stats_note": "\n<i>Time only starts counting after a successful Steam login.</i>",
    "bot.account.guard_confirmation": "\n🔐 Confirm the Steam Hour Booster request in Steam or via the link in the email. Login will continue automatically.",
    "bot.account.guard_mobile": "\n🔐 Enter the Steam Guard code with the button below, or confirm the Steam Hour Booster request in the Steam app.",
    "bot.account.guard_email": "\n📧 Enter the code from the Steam email with the button below.",
    "bot.account.state": "\n\n⚠️ <b>State:</b> {error}",
    "bot.guard.mode.auto": "auto",
    "bot.guard.mode.auto_saved": "auto (secret saved)",
    "bot.guard.mode.manual": "manual",
    # Add-account form
    "bot.add.title": "<b>➕ New account · 1/4</b>\n\n🏷 Send a short name, for example <code>Main</code>.",
    "bot.add.title_invalid": "⚠️ The name must be 1 to 48 characters long. Please try again.",
    "bot.add.username": "<b>➕ New account · 2/4</b>\n\n👤 Send the Steam login.",
    "bot.add.username_invalid": "⚠️ The login must be 1 to 128 characters long. Please try again.",
    "bot.add.password": "<b>➕ New account · 3/4</b>\n\n🔑 Send the Steam password. The message will be deleted if Telegram allows it.",
    "bot.add.password_invalid": "⚠️ The password must be 1 to 512 characters long. Please try again.",
    "bot.add.games": "<b>➕ New account · 4/4</b>\n\n🎯 Send Steam App IDs separated by commas, for example <code>570,730,440</code>.",
    "bot.add.games_error": "⚠️ {error}\n\nSend the Steam App IDs again.",
    # Guard import
    "bot.import.text": (
        "<b>🛡 Steam Guard import</b>\n\n"
        "Send one or more <code>.maFile</code> files as documents (steamguard-cli creates them "
        "in <code>%APPDATA%\\steamguard-cli\\maFiles</code>). The files must not be encrypted. The bot matches "
        "the <code>account_name</code> in each file to the Steam login of a saved account and turns on "
        "automatic Steam Guard for it. The messages will be deleted if Telegram allows it."
    ),
    "bot.import.results_header": "<b>Result:</b>",
    "bot.import.file_default": "file",
    "bot.import.unreadable": "⚠️ {name}: could not be read — {error}",
    "bot.import.no_account": "⚠️ no account with login {username}",
    "bot.import.document_required": "⚠️ Send the <code>.maFile</code> as a document. Text is not accepted here.",
    # Settings menu and field prompts
    "bot.edit.menu": (
        "<b>✏️ Settings: {title}</b>\n\n"
        "🛡 Steam Guard: {guard}\n\n"
        "Choose a field. The password and secret are never shown on screen."
    ),
    "bot.edit.prompt.title": "🏷 Send the new account name.",
    "bot.edit.prompt.username": "👤 Send the new Steam login.",
    "bot.edit.prompt.password": "🔑 Send the new Steam password. The message will be deleted if possible.",
    "bot.edit.prompt.games": "🎯 Send Steam App IDs separated by commas, for example <code>570,730</code>.",
    "bot.edit.prompt.shared_secret": (
        "🛡 Send the <code>shared_secret</code> from the <code>.maFile</code> (steamguard-cli), the entire text of the "
        "<code>.maFile</code>, or upload the <code>.maFile</code> itself as a document. "
        "The bot will then enter the Steam Guard code on its own at login. "
        "The message will be deleted if Telegram allows it."
    ),
    "bot.edit.prompt.custom_game_name": "🎮 Send the name of a third-party game on a single line (up to 64 characters). It will be first in the Steam game list. For example: <code>My game</code>.",
    "bot.edit.field": "<b>✏️ {title}</b>\n\n{prompt}",
    "bot.edit.error": "⚠️ {error}\n\nSend the value again or cancel.",
    "bot.error.custom_game_empty": "Enter a name or use the \"Remove custom game\" button in the settings.",
    "bot.error.mafile_other_login": "This maFile belongs to a different Steam login, check the file.",
    "bot.error.file_too_large": "The file is too large for a maFile (64 KB maximum).",
    "bot.error.download_failed": "Could not download the file from Telegram. Please try again.",
    # Steam Guard code entry
    "bot.guard.empty": "⚠️ The code cannot be empty. Send the code again.",
    "bot.guard.checking": "<b>⏳ Checking the Steam code…</b>\n\nDon't send it again while the check is running.",
    # Delete confirmation
    "bot.delete.confirm": (
        "<b>🗑 Delete account {title}?</b>\n\n"
        "The login, password, game list and saved statistics will be deleted. This cannot be undone."
    ),
    # Log messages
    "bot.log.refresh_failed": (
        "Could not refresh the Telegram screen in chat {chat_id} ({error}). "
        "Retrying in {delay} s, attempt {attempt}. Steam sessions are unaffected."
    ),
    "bot.log.refresh_restored": (
        "Telegram screen refresh in chat {chat_id} recovered after {failures} errors. "
        "No Steam re-login was performed."
    ),
    "bot.log.refresh_forbidden": (
        "Telegram denied access to chat {chat_id}. Screen refresh stopped; "
        "Steam sessions are unaffected."
    ),
    "bot.log.alert_waiting": "Alert for account {account} is waiting for Telegram to recover; retrying in {delay} s",
    "bot.log.alert_failed": "Could not send the alert for account {account}: {error}",
    "bot.log.control_message_unavailable": "Control message {message_id} is unavailable: {error}",
    "bot.log.live_refresh_failed": "Live refresh failed for chat {chat_id}",
    "bot.log.language_commands_failed": "Could not update the bot command menu after the language change: {error}",
}
