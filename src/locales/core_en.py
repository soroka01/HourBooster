"""Core messages (en)."""

MESSAGES = {
    "core.storage.games.invalid": "Enter Steam App IDs as positive numbers separated by commas.",
    "core.storage.games.empty": "Add at least one Steam App ID.",
    "core.storage.games.too_many": "An account can have at most 50 games.",
    "core.storage.games.unreadable": "Could not read the account's game list from the database.",
    "core.storage.title.invalid": "The account name must be 1 to 48 characters long.",
    "core.storage.username.invalid": "The Steam username must be 1 to 128 characters long.",
    "core.storage.password.invalid": "The Steam password must be 1 to 512 characters long.",
    "core.storage.game_id.not_number": "A Steam App ID must be a number.",
    "core.storage.game_id.not_positive": "A Steam App ID must be positive.",
    "core.storage.title.duplicate": "An account with this name already exists.",
    "core.storage.account.create_failed": "Could not create the account.",
    "core.storage.account.update_failed": "Could not update the account.",
    "core.storage.account.not_found": "Account not found.",
    "core.storage.custom_game.invalid": "The custom game name must be a single line of up to 64 characters.",
    "core.storage.field.unknown": "Unknown account field.",
    "core.setup.not_interactive": "Run HourBooster.py --setup in an interactive console.",
    "core.setup.prompt.language": "Language (en/ru) [{current}]: ",
    "core.setup.prompt.token": "Telegram bot token: ",
    "core.setup.prompt.owner": "Telegram owner user ID: ",
    "core.setup.cancelled": "Setup cancelled.",
    "core.setup.invalid": "Enter a valid Telegram token and a positive user ID. Use --setup.",
    "core.main.setup_saved": "Telegram settings saved to SQLite.",
    "core.main.recovered": "Interrupted sessions closed after restart: {count}",
    "core.main.commands_rejected": (
        "Telegram rejected the bot setup request (404/401). "
        "Check the token from @BotFather and save it again with HourBooster.py --setup."
    ),
    "core.main.started": "🎮 Steam Hour Booster started",
    "core.main.config_error": "Configuration error: {error}",
}
