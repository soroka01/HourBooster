# 🎮 Steam Hour Booster

> A private Telegram panel for starting selected Steam App IDs across a dynamic account list and tracking session time locally.

🌐 **Language:** [Русский](README.md) · [English](README_EN.md)

![Python](https://img.shields.io/badge/Python-3.14%2B-3776AB?logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-aiogram%203.4.1-2CA5E0?logo=telegram&logoColor=white)
![Storage](https://img.shields.io/badge/Storage-SQLite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Overview

The bot stores Steam accounts in a local SQLite database and gives the owner one Telegram interface for creating, editing, starting, stopping, and viewing them. After a successful login, a separate `SteamClient` calls `games_played()` with the configured App IDs and remains connected in a daemon thread until the session stops or disconnects.

> [!IMPORTANT]
> Steam usernames and passwords are stored **in plaintext** in SQLite because the client needs the original credentials to sign in. Protect the machine, database backups, and Telegram bot; never publish `config/config.ini` or `data/`.

> [!NOTE]
> `games_played()` reports the selected App IDs to Steam; it does not launch game executables on the machine. Use only accounts you are authorized to manage and follow Steam's rules.

## 🚀 Highlights

| Capability | How it works |
| --- | --- |
| Dynamic accounts | Add accounts through Telegram instead of fixed `[account1..3]` sections |
| Private access | Every message and callback is checked against one `allowed_user_id` |
| One control screen | The bot edits a saved message instead of sending a service-message chain |
| Steam Guard | Mobile two-factor and email authentication codes are supported |
| Local statistics | SQLite stores accumulated time and completed sessions |
| Pagination | Lists are displayed in pages of 6 accounts |
| Legacy migration | Old `[account*]` sections are imported into SQLite once |

From the menu, the owner can:

- add a title, Steam username, password, and up to 50 unique App IDs;
- edit any field while that account has no live session;
- start or stop one Steam client;
- view accumulated and current local time and completed-session count;
- delete an account and its session history after confirmation.

The password is never rendered on the control screen. The bot attempts to delete user messages containing form input and authentication codes, but Telegram can deny deletion.

## 🧭 Interface

```text
/start
  └─ account list
       ├─ ➕ add an account
       └─ open an account card
            ├─ 🚀 start / ⏹ stop
            ├─ 🔐 enter Steam Guard or email code
            ├─ 📊 statistics
            ├─ ✏️ edit title, username, password, or App IDs
            └─ 🗑 delete with confirmation
```

| Command | Action |
| --- | --- |
| `/start` | Open the account list |
| `/menu` | Open the account list |
| `/help` | Show brief instructions |
| `/cancel` | Cancel a form or authentication-code input |

## 🏗️ Architecture

```text
HourBooster.py                  # bot, database, middleware, and polling
config/
└── config.ini.example          # Telegram access and optional DB path
src/
├── config_manager.py           # configuration and legacy [account*] import
├── storage/
│   └── database.py             # accounts, sessions, stats, and UI state
├── steam/
│   └── steam_manager.py        # SteamClient lifecycle and worker threads
└── bot/
    ├── access_middleware.py    # owner-only access
    ├── controller.py           # commands, callbacks, CRUD, and FSM forms
    ├── states.py               # account form and Guard code states
    └── ui.py                   # rendering, pagination, and live refresh
```

Account start flow:

```text
Telegram button
      ↓
SteamSessionManager → SteamClient.login()
      ↓
Guard / email code when requested by Steam
      ↓
EResult.OK → database.start_boost()
      ↓
games_played(App IDs) → run_forever()
      ↓
logout/disconnect → database.stop_boost()
```

## 📋 Requirements

- Python 3.14 or newer (the latest 3.14.6 patch is recommended);
- pip 26.1.2, setuptools 84.0.0, and wheel 0.48.0 (the launchers upgrade them automatically);
- a Telegram bot created through [@BotFather](https://t.me/BotFather);
- the owner's numeric Telegram user ID;
- Steam accounts you are authorized to manage;
- an environment where `steam[client]` can be installed.

## ⚙️ Install and run

```powershell
git clone https://github.com/soroka01/HourBooster.git
cd HourBooster
Copy-Item config\config.ini.example config\config.ini
```

Fill in `config/config.ini`, then choose a launch method.

### Windows

[start.bat](start.bat) creates `.venv`, installs dependencies, and starts the bot:

```powershell
.\start.bat
```

Manual equivalent:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe HourBooster.py
```

### Linux or a macOS-like environment

[start.sh](start.sh) requires `bash` and `python3`:

```bash
cp config/config.ini.example config/config.ini
./start.sh
```

The Unix-like launcher is included but is not exercised by CI; installing `steam[client]` may require additional system packages depending on the platform and Python version.

Both launchers run `pip install -r requirements.txt` on every start. Already satisfied dependencies are not downloaded again.

## 🔧 Configuration

```ini
[telegram]
bot_token = YOUR_BOT_TOKEN_HERE
allowed_user_id = YOUR_TELEGRAM_USER_ID

[storage]
# Optional. Default: data/hour_booster.sqlite3
# database_path = data/hour_booster.sqlite3
```

| Field | Purpose |
| --- | --- |
| `telegram.bot_token` | Telegram bot token |
| `telegram.allowed_user_id` | The only user ID allowed to operate the bot |
| `storage.database_path` | Optional absolute path or path relative to the project root |

`config/config.ini` is required and excluded from Git. Replace the `allowed_user_id` placeholder with a number.

## 🔐 Local data and security

By default, SQLite lives at `data/hour_booster.sqlite3` and contains:

- account titles, Steam usernames, and **plaintext passwords**;
- App ID lists;
- accumulated time and the `active_since` timestamp;
- completed-session history;
- the control-message ID for each Telegram chat.

Recommendations:

- restrict operating-system access to the project directory;
- keep the database and configuration out of public backups;
- revoke the Telegram token if exposure is suspected;
- do not rely on message deletion as the only credential protection;
- back up the database before account deletion if its statistics matter.

## ⏱️ Time accounting

The local timer starts only after Steam returns `EResult.OK`. On a normal stop or disconnect, elapsed time is added to `total_boost_seconds` and the session is marked complete.

> [!WARNING]
> Process shutdown does not stop every Steam worker through a dedicated shutdown hook. When SQLite still contains `active_since`, the next launch closes that session using the new current time. Downtime between process termination and restart can therefore be included in the statistics. These values are local bot accounting, not an independent or guaranteed-accurate Steam playtime source.

## 🔁 Legacy configuration migration

On the first launch with the new storage schema, valid `[account1]`, `[account2]`, and other `[account*]` sections are imported into SQLite. A global migration marker is then stored, so the automatic import is not repeated.

1. Back up `config/config.ini`.
2. Start the bot and verify the imported account cards.
3. Remove Steam credentials from legacy sections after verification.

## 🧪 Limitations and testing

- The repository has no automated tests or CI.
- `steam[client]` is not version-pinned, so its transitive dependency set can change between installations.
- Live refresh updates only the open control screen and uses an interval of at least 2 seconds.
- Steam login and Guard availability depend on Steam and the installed client-library version.
- Module syntax can be checked without credentials:

  ```bash
  python -m compileall -q HourBooster.py src
  ```

## 🩹 Troubleshooting

Diagnose one account by its SQLite ID:

```powershell
.\.venv\Scripts\python.exe debug_login.py 3
.\.venv\Scripts\python.exe debug_login.py 3 --login
.\.venv\Scripts\python.exe debug_login.py 3 --modern
```

Without a flag, only accidental whitespace and control-character checks run.
`--login` attempts one login through the bot's SteamClient; `--modern` checks the
same credentials through Steam's modern authentication API and may trigger a
Steam Guard notification. Neither mode plays games, changes SQLite, saves tokens,
or prints usernames, passwords, or complete response payloads. Legacy
`InvalidPassword` together with modern `eresult: 1` and `auth_session_created: True`
means modern authentication accepted the credentials. The bot's authentication
flow still needs updating; this diagnostic does not migrate it.

| Symptom | Check |
| --- | --- |
| `config/config.ini was not found` | Copy `config.ini.example` first |
| Configuration error | `bot_token` and numeric `allowed_user_id` |
| The bot denies access | Telegram user ID matches the configuration |
| Steam rejects login | Credentials and the requested Guard/email code |
| A session remains `connecting` | Network access, Steam availability, and console logs |
| Statistics grow after restart | The interrupted-session recovery limitation above |
| `steam[client]` does not install | Python version and platform build dependencies |

## 📄 License

Distributed under the [MIT License](LICENSE).

---

🎮 One private screen for accounts, Steam sessions, and clear local statistics.
