# 🎮 Steam Hour Booster

> A private Telegram panel for starting selected Steam App IDs across a dynamic account list and tracking session time locally.

🌐 **Language:** [Русский](README.md) · [English](README_EN.md)

![Python](https://img.shields.io/badge/Python-3.14%2B-3776AB?logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-aiogram%203.31.0-2CA5E0?logo=telegram&logoColor=white)
![Storage](https://img.shields.io/badge/Storage-SQLite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Overview

The bot stores Steam accounts in a local SQLite database and gives the owner one Telegram interface for creating, editing, starting, stopping, and viewing them. After a successful login, a separate `SteamClient` calls `games_played()` with the configured App IDs and remains connected in a daemon thread until the session stops or disconnects.

> [!IMPORTANT]
> Steam usernames and passwords are stored **in plaintext** in SQLite because the client needs the original credentials to sign in. Protect the machine, database backups, and Telegram bot; never publish `data/`.

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

From the menu, the owner can:

- add a title, Steam username, password, and up to 50 unique App IDs;
- edit any field while that account has no live session;
- start or stop one Steam client;
- view accumulated and current local time and completed-session count;
- delete an account and its session history after confirmation.

The password is never rendered on the control screen. The bot attempts to delete user messages containing form input and authentication codes, but Telegram can deny deletion.

## 🧭 Interface

To set a custom Steam status name, stop the account and open **Settings → 🎮 Custom game** (the bot UI is in Russian). Enter one line of up to 64 characters, then start the account again. The custom name is sent first as a non-Steam game, followed by all configured App IDs in their original order. Each account stores its own name in SQLite; **Remove custom game** restores the normal list.

This reports a non-Steam application status; it does not launch an `.exe` or rename library games. Steam privacy settings still control visibility. [Steam's non-Steam games guide](https://help.steampowered.com/en/faqs/view/4B8B-9697-2338-40EC).

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
| `/cancel` | Cancel a form or authentication-code input |

## 🏗️ Architecture

```text
HourBooster.py                  # bot, database, middleware, and polling
data/hour_booster.sqlite3       # accounts and Telegram settings (not in Git)
src/
├── config_manager.py           # SQLite Telegram settings and initial setup
├── storage/
│   └── database.py             # accounts, sessions, stats, and UI state
├── steam/
│   ├── auth.py                 # AuthenticationService + CM token login
│   ├── game_names.py           # Steam app names and cache
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
SteamSessionManager → AuthenticationService → Steam Guard → refresh token
      ↓
Guard / email code when requested by Steam
      ↓
TokenSteamClient.login_token() → EResult.OK → database.start_boost()
      ↓
games_played(App IDs) → connected session
      ↓
logout/disconnect → database.stop_boost()
```

## 📋 Requirements

- Python 3.14;
- pip 26.1.2, setuptools 84.0.0, and wheel 0.48.0 (the launchers upgrade them automatically);
- a Telegram bot created through [@BotFather](https://t.me/BotFather);
- the owner's numeric Telegram user ID;
- Steam accounts you are authorized to manage;
- an environment where `steam[client]` can be installed.

## ⚙️ Install and run

```powershell
git clone https://github.com/soroka01/HourBooster.git
cd HourBooster
```

On first launch, enter the Telegram bot token and owner ID in the console. They are saved in SQLite; add Steam accounts through Telegram.

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

### Linux and macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python HourBooster.py
```

## 🔧 Configuration

Telegram settings live in the `app_settings` table in the account database. Stop the bot before changing its token or owner ID:

```powershell
.\.venv\Scripts\python.exe HourBooster.py --setup
```

Token input is hidden. The command exits after saving; start the bot normally afterwards. The default is `data/hour_booster.sqlite3` relative to the project directory. Use `--database PATH` to select another database, including with `--setup`.

## 🔐 Local data and security

By default, SQLite lives at `data/hour_booster.sqlite3` and contains:

- the Telegram bot token and owner ID;
- account titles, Steam usernames, and **plaintext passwords**;
- App ID lists;
- accumulated time and the `active_since` timestamp;
- completed-session history;
- the control-message ID for each Telegram chat.

Recommendations:

- restrict operating-system access to the project directory;
- keep the database out of public backups;
- revoke the Telegram token if exposure is suspected;
- do not rely on message deletion as the only credential protection;
- back up the database before account deletion if its statistics matter.

## ⏱️ Time accounting

The local timer starts only after Steam returns `EResult.OK`. On a normal stop or disconnect, elapsed time is added to `total_boost_seconds` and the session is marked complete.

> [!WARNING]
> Normal shutdown stops Steam workers and records session durations. After an unexpected termination, when SQLite still contains `active_since`, the next launch closes that session using the new current time. Downtime between process termination and restart can therefore be included in the statistics. These values are local bot accounting, not an independent or guaranteed-accurate Steam playtime source.

## 🔁 Updating

Back up SQLite, run `git pull`, and restart the bot. Existing accounts and statistics remain in the database. If Telegram settings are not stored there yet, enter them on first launch. INI account import has been removed.

## ⚠️ Limitations

- Only the open card refreshes, at intervals of at least two seconds.
- Game names are fetched from Steam and cached; IDs remain visible when names are unavailable. Long names are shortened to fit the message limit.
- Login uses modern Steam AuthenticationService with an RSA-encrypted password, followed by a Steam client login using a refresh token.
- Approve the Steam Hour Booster request in Steam or submit a Guard/email code through the bot within 5 minutes. Tokens are not saved in SQLite or displayed in messages.
- Login availability depends on Steam; parental game restrictions still apply.

## 🩹 Troubleshooting

| Symptom | Check |
| --- | --- |
| Configuration error | Run `HourBooster.py --setup` again |
| The bot denies access | Telegram user ID matches the SQLite settings |
| Steam rejects login | Credentials and the requested Guard/email code |
| A session remains `connecting` | Network access, Steam availability, and console logs |
| Statistics grow after restart | The interrupted-session recovery limitation above |
| `steam[client]` does not install | Python version and platform build dependencies |

## 📄 License

Distributed under the [MIT License](LICENSE).

---

🎮 One private screen for accounts, Steam sessions, and clear local statistics.
