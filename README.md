# 🎮 Steam Hour Booster

> Приватная Telegram-панель для запуска выбранных Steam App ID на динамическом списке аккаунтов и локального учёта времени сессий.

🌐 **Язык:** [Русский](README.md) · [English](README_EN.md)

![Python](https://img.shields.io/badge/Python-3.14%2B-3776AB?logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-aiogram%203.4.1-2CA5E0?logo=telegram&logoColor=white)
![Storage](https://img.shields.io/badge/Storage-SQLite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Обзор

Бот хранит Steam-аккаунты в локальной SQLite-базе и даёт владельцу один Telegram-интерфейс для добавления, редактирования, запуска, остановки и просмотра статистики. После успешного входа отдельный `SteamClient` вызывает `games_played()` с настроенными App ID и остаётся подключённым в daemon thread до остановки или разрыва сессии.

> [!IMPORTANT]
> Steam-логины и пароли хранятся в SQLite **в открытом виде**, потому что клиенту нужны исходные credentials для входа. Защитите компьютер, backup базы и Telegram-бота; не публикуйте `config/config.ini` и `data/`.

> [!NOTE]
> `games_played()` сообщает Steam о выбранных App ID, но не запускает игровые executables на компьютере. Используйте только аккаунты, которыми вы вправе управлять, и соблюдайте правила Steam.

## 🚀 Основные возможности

| Возможность | Как работает |
| --- | --- |
| Динамические аккаунты | Аккаунты добавляются через Telegram, без фиксированных `[account1..3]` |
| Приватный доступ | Все messages и callbacks проходят проверку одного `allowed_user_id` |
| Один control screen | Бот редактирует сохранённое сообщение вместо цепочки служебных ответов |
| Steam Guard | Поддерживаются mobile two-factor и email auth codes |
| Локальная статистика | SQLite хранит суммарное время и завершённые sessions |
| Пагинация | Список выводится страницами по 6 аккаунтов |
| Legacy migration | Старые `[account*]` sections однократно импортируются в SQLite |

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
config/
└── config.ini.example          # Telegram access и optional DB path
src/
├── config_manager.py           # config и legacy [account*] import
├── storage/
│   └── database.py             # accounts, sessions, stats и UI state
├── steam/
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
SteamSessionManager → SteamClient.login()
      ↓
Guard / email code, если Steam запросил его
      ↓
EResult.OK → database.start_boost()
      ↓
games_played(App IDs) → run_forever()
      ↓
logout/disconnect → database.stop_boost()
```

## 📋 Требования

- Python 3.14 или новее (рекомендуется актуальный патч 3.14.6);
- pip 26.1.2, setuptools 84.0.0 и wheel 0.48.0 (launcher обновляет их автоматически);
- Telegram-бот, созданный через [@BotFather](https://t.me/BotFather);
- числовой Telegram user ID владельца;
- Steam-аккаунты, которыми вы вправе управлять;
- системная среда, в которой устанавливается `steam[client]`.

## ⚙️ Установка и запуск

```powershell
git clone https://github.com/soroka01/HourBooster.git
cd HourBooster
Copy-Item config\config.ini.example config\config.ini
```

Заполните `config/config.ini`, затем выберите способ запуска.

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

### Linux или macOS-подобная среда

[start.sh](start.sh) требует `bash` и `python3`:

```bash
cp config/config.ini.example config/config.ini
./start.sh
```

Unix-like launcher присутствует, но не проверяется CI; установка `steam[client]` может потребовать дополнительные system packages в зависимости от платформы и версии Python.

Оба launcher выполняют `pip install -r requirements.txt` при каждом запуске. Уже удовлетворённые зависимости повторно не скачиваются.

## 🔧 Конфигурация

```ini
[telegram]
bot_token = YOUR_BOT_TOKEN_HERE
allowed_user_id = YOUR_TELEGRAM_USER_ID

[storage]
# Optional. Default: data/hour_booster.sqlite3
# database_path = data/hour_booster.sqlite3
```

| Поле | Назначение |
| --- | --- |
| `telegram.bot_token` | Token Telegram-бота |
| `telegram.allowed_user_id` | Единственный user ID, которому разрешено управление |
| `storage.database_path` | Optional absolute path или путь относительно корня проекта |

`config/config.ini` обязателен и исключён из Git. Placeholder `allowed_user_id` должен быть заменён числом.

## 🔐 Локальные данные и безопасность

SQLite по умолчанию находится в `data/hour_booster.sqlite3` и содержит:

- названия аккаунтов, Steam logins и **plaintext passwords**;
- списки App ID;
- суммарное время и отметку `active_since`;
- историю завершённых sessions;
- ID control message для каждого Telegram chat.

Рекомендации:

- ограничьте доступ к каталогу проекта средствами операционной системы;
- не помещайте базу и config в публичные backups;
- отзовите Telegram token при подозрении на утечку;
- не полагайтесь на удаление messages как на единственную защиту credentials;
- перед удалением аккаунта сделайте backup, если нужна его статистика.

## ⏱️ Как считается время

Локальный timer начинается только после `EResult.OK` от Steam. При обычной остановке или disconnect длительность до текущего момента добавляется в `total_boost_seconds`, а session помечается завершённой.

> [!WARNING]
> При завершении процесса бот не останавливает все Steam workers отдельным shutdown hook. Если в SQLite остаётся `active_since`, следующий запуск закрывает такую session своим текущим временем. Поэтому downtime между остановкой процесса и следующим запуском может попасть в статистику. Эти значения — локальный учёт работы бота, а не независимая или гарантированно точная Steam playtime.

## 🔁 Миграция старой конфигурации

При первом запуске новой storage-схемы valid sections `[account1]`, `[account2]` и другие `[account*]` импортируются в SQLite. После первой попытки в базе ставится общий migration marker, и повторный автоматический import не выполняется.

1. Сделайте backup `config/config.ini`.
2. Запустите бота и проверьте импортированные карточки.
3. Удалите Steam credentials из legacy sections после проверки.

## 🧪 Ограничения и тестирование

- Репозиторий не содержит automated tests и CI.
- Зависимость `steam[client]` не закреплена по версии, поэтому её transitive dependency set может измениться между установками.
- Live refresh обновляет только открытый control screen и работает с интервалом не меньше 2 секунд.
- Фактическая доступность Steam login и Guard flows зависит от Steam и используемой версии client library.
- Синтаксис модулей можно проверить без credentials:

  ```bash
  python -m compileall -q HourBooster.py src
  ```

## 🩹 Решение проблем

Для диагностики входа одного аккаунта по его ID в SQLite:

```powershell
.\.venv\Scripts\python.exe debug_login.py 3
.\.venv\Scripts\python.exe debug_login.py 3 --login
.\.venv\Scripts\python.exe debug_login.py 3 --modern
```

Без флага проверяются только признаки случайных пробелов и управляющих символов.
`--login` делает одну попытку через используемый ботом SteamClient;
`--modern` проверяет те же данные через современный API авторизации Steam и может
вызвать уведомление Steam Guard. Диагностика не запускает игры, не меняет SQLite,
не сохраняет токены и не выводит логин, пароль или содержимое ответов целиком.
Если старый вход возвращает `InvalidPassword`, а современный — `eresult: 1` и
`auth_session_created: True`, данные приняты современным API: требуется обновление
пути авторизации бота. Эта проверка сама по себе не переводит бот на новый вход.

| Симптом | Что проверить |
| --- | --- |
| `config/config.ini was not found` | Скопирован ли `config.ini.example` |
| Ошибка конфигурации | `bot_token` и числовой `allowed_user_id` |
| Нет доступа к боту | Совпадает ли Telegram user ID с config |
| Steam отклоняет login | Credentials и требуемый Guard/email code |
| Сессия остаётся в `connecting` | Network access, Steam availability и logs в консоли |
| Статистика выросла после restart | Ограничение recovery незакрытой session выше |
| Не ставится `steam[client]` | Python version и platform build dependencies |

## 📄 Лицензия

Проект распространяется по [лицензии MIT](LICENSE).

---

🎮 Один приватный экран для аккаунтов, Steam sessions и понятной локальной статистики.
