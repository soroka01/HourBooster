# 🎮 Steam Hour Booster

> Telegram-панель для запуска Steam-клиентов и учёта игрового времени до трёх аккаунтов из одного приватного меню.

🌐 **Язык:** [Русский](README.md) · [English](README_EN.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Aiogram](https://img.shields.io/badge/Telegram-aiogram%203-2CA5E0?logo=telegram&logoColor=white)
![Steam](https://img.shields.io/badge/Steam-client-171A21?logo=steam&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Идея проекта

Бот заменяет ручной вход в несколько Steam-клиентов простым Telegram-меню. Владелец выбирает аккаунт, запускает или останавливает сессию, видит её состояние и при необходимости вводит Steam Guard или email-код прямо в диалоге с ботом.

| Что | Как работает |
| --- | --- |
| 👤 Доступ | Только Telegram user ID из `allowed_user_id` |
| 🎮 Аккаунты | До трёх независимых секций: `account1`, `account2`, `account3` |
| 🧭 Управление | Inline-кнопки: запуск, остановка, статус и обновление меню |
| 🔐 Авторизация | Поддержка мобильного Steam Guard и email-кодов |
| 🔄 Сессии | Каждый Steam-клиент запускается в отдельном daemon-потоке |

## 🚀 Возможности

- **Приватное меню** — middleware не допускает к командам и кнопкам посторонних пользователей.
- **Управление до 3 аккаунтами** — можно оставить только нужные секции конфигурации.
- **Запуск игр по Steam App ID** — клиент вызывает `games_played` для списка игр аккаунта.
- **Статус сессии** — главное меню показывает число активных аккаунтов; экран аккаунта показывает логин, состояние и назначенные игры.
- **Безопасная остановка** — остановка отключает Steam-клиент и ожидает завершения потока с ограничением по времени.
- **Steam Guard и Email** — бот переводит пользователя в отдельное состояние ввода кода, позволяет отменить его кнопкой или командой `/cancel` и удаляет сообщение с кодом, когда Telegram разрешает это действие.
- **Редактирование экрана по кнопкам** — переходы внутри меню обновляют сообщение на месте вместо лишней цепочки ответов.

## 🗺️ Сценарий работы

```text
/start
  └─ выбрать аккаунт
       ├─ ▶️ Запустить
       │    └─ при необходимости ввести Steam Guard / email-код
       ├─ ⏹️ Остановить
       └─ 📊 Статистика
```

Доступные команды:

| Команда | Назначение |
| --- | --- |
| `/start` | Открыть главное меню аккаунтов |
| `/help` | Показать краткую инструкцию |
| `/cancel` | Отменить ввод Steam Guard или email-кода |

## 🏗️ Структура

```text
steam_HourBooster/
├── HourBooster.py              # Точка входа: bot, dispatcher и callbacks
├── start.bat                   # Самостоятельный Windows launcher
├── requirements.txt            # aiogram и Steam client
├── config/
│   ├── config.ini.example      # Шаблон без секретов
│   └── config.ini              # Локальная конфигурация владельца
└── src/
    ├── config_manager.py       # Чтение Telegram и Steam-настроек
    ├── steam/
    │   └── steam_manager.py    # Логин, games_played и остановка клиента
    └── bot/
        ├── access_middleware.py # Ограничение по Telegram user ID
        ├── handlers.py          # Запуск, остановка и состояние аккаунта
        ├── states.py            # FSM для кодов Steam Guard / Email
        └── ui_manager.py        # Тексты и inline-клавиатуры
```

## ⚙️ Установка и запуск

Требуется **Python 3.8+** и доступ к Telegram и Steam.

### 1. Получите исходники

```powershell
git clone https://github.com/soroka01/HourBooster.git
cd HourBooster
```

### 2. Подготовьте локальную конфигурацию

`config/config.ini` содержит токен Telegram-бота и Steam-учётные данные. Создайте его из шаблона и не добавляйте в Git:

```powershell
Copy-Item config\config.ini.example config\config.ini
```

Минимальная схема:

```ini
[telegram]
bot_token = YOUR_BOT_TOKEN
allowed_user_id = YOUR_TELEGRAM_USER_ID

[account1]
username = your_steam_login
password = your_steam_password
games = 570,730,440
```

Добавьте `account2` и `account3` только если они нужны. В `games` указываются Steam App ID через запятую; найти их можно в [SteamDB](https://steamdb.info/search/).

### 3. Запустите

На Windows самый простой путь — `start.bat`. Он проверяет наличие `config/config.ini`, при необходимости создаёт локальную `.venv` и устанавливает зависимости из `requirements.txt`.

Либо выполните всё вручную:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python HourBooster.py
```

На Linux/macOS используйте те же команды с вашим интерпретатором Python и путями виртуального окружения:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python HourBooster.py
```

## 🔐 Настройка доступа и Steam Guard

1. Создайте Telegram-бота через [@BotFather](https://t.me/BotFather) и вставьте токен в `bot_token`.
2. Узнайте свой числовой Telegram user ID, например через [@userinfobot](https://t.me/userinfobot), и укажите его в `allowed_user_id`.
3. Отправьте `/start`, выберите аккаунт и нажмите «Запустить».
4. Если Steam запросит дополнительное подтверждение, отправьте полученный Steam Guard или email-код в чат с ботом. Для отмены используйте `/cancel` или кнопку «Отменить».

> ⚠️ `allowed_user_id` — не список, а один ID. Бот рассчитан на персональное использование владельцем конфигурации.

## 🛡️ Безопасность и ограничения

- Никогда не публикуйте `config/config.ini`, токен Telegram или Steam-пароли.
- Используйте только аккаунты, которыми имеете право управлять, и соблюдайте правила Steam.
- Steam Guard и email-коды — одноразовые чувствительные данные; не пересылайте их третьим лицам.
- Локальные учётные данные читаются приложением для входа в Steam. Защитите компьютер и доступ к его файловой системе.
- Бот управляет клиентскими сессиями; он не гарантирует начисление часов, доступность Steam или отсутствие ограничений со стороны платформы.

## 🧪 Проверка изменений

В проект не добавляются production-тесты. Для безопасных изменений достаточно буферно проверить:

- компиляцию Python-модулей;
- наличие `config/config.ini` перед запуском;
- вход с тестовым аккаунтом;
- запуск, статус и остановку одной сессии;
- обработку Steam Guard и `/cancel`.

## 📄 Лицензия

Проект распространяется по лицензии [MIT](LICENSE).

---

💙 Сделано для аккуратного личного управления Steam-сессиями через Telegram.
