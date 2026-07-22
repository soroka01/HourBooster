# 🎮 Steam Hour Booster

> A private Telegram control panel for launching Steam clients and tracking game time across up to three accounts.

🌐 **Language:** [Русский](README.md) · [English](README_EN.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Aiogram](https://img.shields.io/badge/Telegram-aiogram%203-2CA5E0?logo=telegram&logoColor=white)
![Steam](https://img.shields.io/badge/Steam-client-171A21?logo=steam&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Project concept

The bot replaces manually signing into several Steam clients with a simple Telegram menu. The owner selects an account, starts or stops its session, sees its state, and enters a Steam Guard or email code in the bot chat when Steam requests one.

| Area | How it works |
| --- | --- |
| 👤 Access | Only the Telegram user ID in `allowed_user_id` can use the bot |
| 🎮 Accounts | Up to three independent sections: `account1`, `account2`, and `account3` |
| 🧭 Controls | Inline buttons for start, stop, status, and menu refresh |
| 🔐 Authentication | Mobile Steam Guard and email-code flows are supported |
| 🔄 Sessions | Each Steam client runs in its own daemon thread |

## 🚀 Features

- **Private menu** — middleware blocks commands and button callbacks from unauthorized users.
- **Up to 3 accounts** — keep only the account sections you need in the configuration.
- **Start games by Steam App ID** — the client calls `games_played` for the account's game list.
- **Session state** — the main menu shows the active-account count; the account screen shows its login, state, and configured games.
- **Safe stop** — stopping disconnects the Steam client and waits for its thread with a timeout.
- **Steam Guard and email codes** — the bot moves the owner into a dedicated input state, supports cancellation by button or `/cancel`, and removes the code message when Telegram permits it.
- **In-place menu updates** — button navigation edits the current screen instead of creating a noisy reply chain.

## 🗺️ Workflow

```text
/start
  └─ choose an account
       ├─ ▶️ Start
       │    └─ enter a Steam Guard / email code if requested
       ├─ ⏹️ Stop
       └─ 📊 Statistics
```

Available commands:

| Command | Purpose |
| --- | --- |
| `/start` | Open the account menu |
| `/help` | Show short instructions |
| `/cancel` | Cancel Steam Guard or email-code input |

## 🏗️ Project structure

```text
steam_HourBooster/
├── HourBooster.py              # Entry point: bot, dispatcher, and callbacks
├── start.bat                   # Self-contained Windows launcher
├── requirements.txt            # aiogram and Steam client dependencies
├── config/
│   ├── config.ini.example      # Secret-free template
│   └── config.ini              # Owner's local configuration
└── src/
    ├── config_manager.py       # Reads Telegram and Steam settings
    ├── steam/
    │   └── steam_manager.py    # Login, games_played, and client stop
    └── bot/
        ├── access_middleware.py # Telegram user-ID restriction
        ├── handlers.py          # Start, stop, and account state
        ├── states.py            # FSM for Steam Guard / email codes
        └── ui_manager.py        # Text and inline keyboards
```

## ⚙️ Install and run

Requires **Python 3.8+** plus access to Telegram and Steam.

### 1. Get the source

```powershell
git clone https://github.com/soroka01/HourBooster.git
cd HourBooster
```

### 2. Prepare local configuration

`config/config.ini` contains the Telegram bot token and Steam credentials. Create it from the template and never commit it:

```powershell
Copy-Item config\config.ini.example config\config.ini
```

Minimal layout:

```ini
[telegram]
bot_token = YOUR_BOT_TOKEN
allowed_user_id = YOUR_TELEGRAM_USER_ID

[account1]
username = your_steam_login
password = your_steam_password
games = 570,730,440
```

Add `account2` and `account3` only when needed. `games` contains comma-separated Steam App IDs; look them up in [SteamDB](https://steamdb.info/search/).

### 3. Start the bot

On Windows, use `start.bat`. It checks for `config/config.ini`, creates a local `.venv` when needed, and installs `requirements.txt`.

Or run the project manually:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python HourBooster.py
```

On Linux/macOS, use the equivalent Python executable and virtual-environment paths:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python HourBooster.py
```

## 🔐 Access and Steam Guard setup

1. Create a Telegram bot through [@BotFather](https://t.me/BotFather) and put its token in `bot_token`.
2. Find your numeric Telegram user ID, for example through [@userinfobot](https://t.me/userinfobot), and set `allowed_user_id`.
3. Send `/start`, choose an account, and press **Start**.
4. If Steam requests an additional confirmation, send the Steam Guard or email code to the bot. Use `/cancel` or the **Cancel** button to stop the flow.

> ⚠️ `allowed_user_id` is one ID, not a list. The bot is designed for personal use by the owner of the configuration.

## 🛡️ Security and limitations

- Never publish `config/config.ini`, a Telegram token, or Steam passwords.
- Use only accounts you are authorized to manage and follow Steam's rules.
- Steam Guard and email codes are sensitive one-time values; never send them to anyone else.
- The application reads local credentials to log into Steam. Secure the machine and its file-system access.
- The bot controls client sessions; it does not guarantee time accrual, Steam availability, or the absence of platform-side restrictions.

## 🧪 Change verification

The repository does not include production tests. For safe changes, use buffer checks:

- compile Python modules;
- check for `config/config.ini` before launch;
- sign in with a test account;
- start, inspect, and stop one session;
- test the Steam Guard flow and `/cancel`.

## 📄 License

This project is available under the [MIT License](LICENSE).

---

💙 Built for tidy personal control of Steam sessions through Telegram.
