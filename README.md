# 🎮 Steam Hour Booster

> Приватная Telegram-панель для запуска выбранных Steam App ID на динамическом списке аккаунтов и локального учёта времени сессий.

🌐 **Язык:** [Русский](README.md) · [English](README_EN.md)

![Python](https://img.shields.io/badge/Python-3.14%2B-3776AB?logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-aiogram%203.31.0-2CA5E0?logo=telegram&logoColor=white)
![Storage](https://img.shields.io/badge/Storage-SQLite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Обзор

Бот хранит Steam-аккаунты в локальной SQLite-базе и даёт владельцу один Telegram-интерфейс для добавления, редактирования, запуска, остановки и просмотра статистики. После успешного входа отдельный `SteamClient` вызывает `games_played()` с настроенными App ID и остаётся подключённым в daemon thread до остановки или разрыва сессии.

> [!IMPORTANT]
> Steam-логины и пароли хранятся в SQLite **в открытом виде**, потому что клиенту нужны исходные credentials для входа. Защитите компьютер, backup базы и Telegram-бота; не публикуйте `data/`.

> [!NOTE]
> `games_played()` сообщает Steam о выбранных App ID, но не запускает игровые executables на компьютере. Используйте только аккаунты, которыми вы вправе управлять, и соблюдайте правила Steam.

## 🚀 Основные возможности

| Возможность | Как работает |
| --- | --- |
| Динамические аккаунты | Аккаунты добавляются через Telegram, без ограничения тремя записями |
| Приватный доступ | Все messages и callbacks проходят проверку одного `allowed_user_id` |
| Один control screen | Бот редактирует сохранённое сообщение вместо цепочки служебных ответов |
| Steam Guard | Код из приложения или email; подтверждение запроса в приложении |
| Локальная статистика | SQLite хранит суммарное время и завершённые sessions |
| Пагинация | Список выводится страницами по 6 аккаунтов |

Через меню можно:

- добавить название, Steam login, пароль и до 50 уникальных App ID;
- изменить любое поле, когда сессия аккаунта не активна;
- запустить или остановить отдельный Steam client;
- посмотреть суммарное и текущее локальное время и число завершённых sessions;
- удалить аккаунт вместе с его session history после подтверждения.

Пароль никогда не выводится на control screen. Бот пытается удалить пользовательские messages с вводом форм и auth codes, но Telegram может запретить удаление.

## 🧭 Интерфейс

```text
/start
  └─ список аккаунтов
       ├─ ➕ добавить аккаунт
       └─ открыть карточку
            ├─ 🚀 запустить / ⏹ остановить
            ├─ 🔐 ввести Steam Guard или email code
            ├─ 📊 статистика
            ├─ ✏️ изменить название, login, пароль или App ID
            └─ 🗑 удалить с подтверждением
```

| Команда | Действие |
| --- | --- |
| `/start` | Открыть список аккаунтов |
| `/menu` | Открыть список аккаунтов |
| `/cancel` | Отменить форму или ввод auth code |

## 🏗️ Архитектура

```text
HourBooster.py                  # bot, database, middleware и polling
data/hour_booster.sqlite3       # аккаунты и настройки Telegram (вне Git)
src/
├── config_manager.py           # настройки Telegram в SQLite и первый запуск
├── storage/
│   └── database.py             # accounts, sessions, stats и UI state
├── steam/
│   ├── auth.py                 # AuthenticationService + CM token login
│   ├── game_names.py           # Steam app names and cache
│   └── steam_manager.py        # SteamClient lifecycle и worker threads
└── bot/
    ├── access_middleware.py    # owner-only access
    ├── controller.py           # commands, callbacks, CRUD и FSM forms
    ├── states.py               # account form и Guard code states
    └── ui.py                   # rendering, pagination и live refresh
```

Поток запуска аккаунта:

```text
Telegram button
      ↓
SteamSessionManager → AuthenticationService → Steam Guard → refresh token
      ↓
Guard / email code, если Steam запросил его
      ↓
TokenSteamClient.login_token() → EResult.OK → database.start_boost()
      ↓
games_played(App IDs) → connected session
      ↓
logout/disconnect → database.stop_boost()
```

## 📋 Требования

- Python 3.14;
- pip 26.1.2, setuptools 84.0.0 и wheel 0.48.0 (launcher обновляет их автоматически);
- Telegram-бот, созданный через [@BotFather](https://t.me/BotFather);
- числовой Telegram user ID владельца;
- Steam-аккаунты, которыми вы вправе управлять;
- системная среда, в которой устанавливается `steam[client]`.

## ⚙️ Установка и запуск

```powershell
git clone https://github.com/soroka01/HourBooster.git
cd HourBooster
```

При первом запуске введите токен Telegram-бота и ID владельца в консоли. Они сохранятся в SQLite; аккаунты добавляются через Telegram.

### Windows

[start.bat](start.bat) создаёт `.venv`, устанавливает зависимости и запускает бота:

```powershell
.\start.bat
```

Ручной эквивалент:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe HourBooster.py
```

### Linux и macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python HourBooster.py
```

## 🔧 Конфигурация

Настройки Telegram хранятся в таблице `app_settings` той же SQLite-базы, что и аккаунты. Для изменения токена или ID владельца остановите бота и выполните:

```powershell
.\.venv\Scripts\python.exe HourBooster.py --setup
```

Токен вводится скрыто. После сохранения команда завершится; запустите бота обычным способом. По умолчанию используется `data/hour_booster.sqlite3` относительно каталога проекта. Другую базу можно выбрать ключом `--database PATH`, в том числе вместе с `--setup`.

## 🔐 Локальные данные и безопасность

SQLite по умолчанию находится в `data/hour_booster.sqlite3` и содержит:

- токен Telegram-бота и ID владельца;
- названия аккаунтов, Steam logins и **plaintext passwords**;
- списки App ID;
- суммарное время и отметку `active_since`;
- историю завершённых sessions;
- ID control message для каждого Telegram chat.

Рекомендации:

- ограничьте доступ к каталогу проекта средствами операционной системы;
- не помещайте базу в публичные backups;
- отзовите Telegram token при подозрении на утечку;
- не полагайтесь на удаление messages как на единственную защиту credentials;
- перед удалением аккаунта сделайте backup, если нужна его статистика.

## ⏱️ Как считается время

Локальный timer начинается только после `EResult.OK` от Steam. При обычной остановке или disconnect длительность до текущего момента добавляется в `total_boost_seconds`, а session помечается завершённой.

> [!WARNING]
> При обычной остановке бот завершает Steam workers и фиксирует время сессий. При аварийном завершении, если в SQLite остаётся `active_since`, следующий запуск закрывает такую session своим текущим временем. Поэтому downtime между остановкой процесса и следующим запуском может попасть в статистику. Эти значения — локальный учёт работы бота, а не независимая или гарантированно точная Steam playtime.

## 🔁 Обновление

Сохраните резервную копию SQLite, выполните `git pull` и перезапустите бота. Существующие аккаунты и статистика остаются в БД. Если настройки Telegram ещё не сохранены в ней, укажите их при первом запуске. Импорт аккаунтов из INI удалён.

## ⚠️ Ограничения

- Обновляется только открытая карточка с интервалом не меньше 2 секунд.
- Названия игр загружаются из Steam и кэшируются; при недоступности названия отображается ID. Длинные названия сокращаются до лимита сообщения.
- Вход выполняется через современный Steam AuthenticationService. Пароль передаётся в RSA-зашифрованном виде, а Steam-клиент входит по refresh token.
- Подтвердите запрос Steam Hour Booster в приложении Steam или введите код через бота. Запрос действует до 5 минут. Токены не сохраняются в БД и не выводятся в сообщения.
- Доступность входа зависит от Steam; семейные ограничения на игры продолжают действовать.

## 🩹 Решение проблем

| Симптом | Что проверить |
| --- | --- |
| Ошибка конфигурации | Повторите `HourBooster.py --setup` |
| Нет доступа к боту | Совпадает ли Telegram user ID с настройками SQLite |
| Steam отклоняет login | Credentials и требуемый Guard/email code |
| Сессия остаётся в `connecting` | Network access, Steam availability и logs в консоли |
| Статистика выросла после restart | Ограничение recovery незакрытой session выше |
| Не ставится `steam[client]` | Python version и platform build dependencies |

## 📄 Лицензия

Проект распространяется по [лицензии MIT](LICENSE).

---

🎮 Один приватный экран для аккаунтов, Steam sessions и понятной локальной статистики.
