# 🎮 Steam Hour Booster

> A private Telegram control panel for managing any number of Steam accounts, launching games, and accurately tracking boost time.

🌐 **Language:** [Русский](README.md) · [English](README_EN.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Aiogram](https://img.shields.io/badge/Telegram-aiogram%203-2CA5E0?logo=telegram&logoColor=white)
![SQLite](https://img.shields.io/badge/Storage-SQLite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ What changed

The bot is no longer limited to `account1..account3` configuration sections. Accounts, Steam App IDs, and statistics live in a local SQLite database and are fully managed through Telegram: add, edit, and delete everything from one control screen.

| Capability | How it works |
| --- | --- |
| ♾️ Any number of accounts | SQLite replaces three hard-coded sections; lists are paginated in groups of six |
| 🧭 One screen | The bot edits one control message instead of filling the chat with replies |
| ⏱ Accurate statistics | Time starts only after a successful Steam login and is persisted when the session stops |
| 🔐 Private access | Only the `allowed_user_id` in local configuration can operate the bot |
| 🔄 Migration | Legacy `[account*]` sections are imported into SQLite once on first launch |

## 🚀 Features

- **Account CRUD in the bot** — add a title, login, password, and game list; edit every field; delete with confirmation.
- **Pagination for large lists** — the interface remains usable with 100+ accounts.
- **Safe UX** — passwords are never shown; the bot attempts to delete user messages containing passwords or Steam Guard codes after processing.
- **Steam Guard and email** — the owner moves into a focused code-entry state with cancel controls and no new service screens.
- **Live state** — active account cards refresh every two seconds by editing the same message.
- **Statistics** — total time, current-session time, and completed-session count for each account.
- **Restart resilience** — an unfinished active session is closed in statistics when the app starts again.

## 🗺️ Interface flow

```text
/start
  └─ 🎮 account list
       ├─ ➕ Add account
       └─ open an account card
            ├─ 🚀 Start / ⏹️ Stop
            ├─ 📊 Statistics
            ├─ ✏️ Settings
            │    ├─ title
            │    ├─ Steam login
            │    ├─ password
            │    └─ Steam App IDs
            └─ 🗑 Delete with confirmation
```

Commands:

| Command | Action |
| --- | --- |
| `/start`, `/menu` | Open the main screen |
| `/help` | Show short instructions |
| `/cancel` | Cancel Steam Guard, email-code, or form input |

## 🏗️ Architecture

```text
HourBooster/
├── HourBooster.py              # Bot, database, and middleware bootstrap
├── start.bat / start.sh         # Self-contained Windows/Linux launchers
├── config/
│   └── config.ini.example       # Token, owner ID, and optional database path only
└── src/
    ├── config_manager.py        # Telegram configuration + legacy-account migration
    ├── storage/
    │   └── database.py          # SQLite accounts, sessions, stats, and UI message
    ├── steam/
    │   └── steam_manager.py     # Steam threads, Guard, start/stop, and time accounting
    └── bot/
        ├── controller.py        # CRUD, callbacks, forms, and navigation
        ├── ui.py                # One message, live refresh, and keyboards
        ├── states.py            # FSM for forms and Steam codes
        └── access_middleware.py # Telegram user-ID restriction
```

## ⚙️ Install

Requires **Python 3.8+**, a Telegram bot, and Steam accounts you are authorized to manage.

```powershell
git clone https://github.com/soroka01/HourBooster.git
cd HourBooster
Copy-Item config\config.ini.example config\config.ini
```

Fill in only Telegram settings:

```ini
[telegram]
bot_token = YOUR_BOT_TOKEN
allowed_user_id = YOUR_TELEGRAM_USER_ID

[storage]
# Optional. data/hour_booster.sqlite3 is the default.
# database_path = data/hour_booster.sqlite3
```

Then start:

```powershell
# Windows: creates .venv and installs dependencies when necessary
.\start.bat

# Or manually
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python HourBooster.py
```

On Linux/macOS:

```bash
cp config/config.ini.example config/config.ini
./start.sh
```

## 🔁 Legacy configuration migration

If an existing `config/config.ini` still has `[account1]`, `[account2]`, or other account sections, the bot imports valid accounts into SQLite on the first launch after the update. Once you verify the migration, remove Steam logins and passwords from the configuration: manage them only through the Telegram menu afterwards.

> ⚠️ Import runs once. Back up `config/config.ini` before updating and never publish it.

## 🔐 Security

- Never commit `config/config.ini`, the SQLite database in `data/`, or logs.
- Steam passwords and game lists are stored locally in SQLite so the bot can log in. Secure the machine and disk access.
- `allowed_user_id` is one numeric Telegram owner ID, not a multi-user list.
- Steam Guard and email codes are sensitive one-time values. Never forward them to anyone else.
- Use only accounts you are authorized to manage and follow Steam's rules.

## 🧪 Buffer checks

No production tests are added to the repository. Before publishing, check:

- Python module compilation;
- creating 100 SQLite accounts and pagination;
- account creation, editing, and deletion;
- accurate start/stop duration accounting;
- `git diff --check`.

## 📄 License

This project is available under the [MIT License](LICENSE).

---

💙 Fewer manual Steam clients, more clarity and control from Telegram.
