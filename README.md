# Steam Hour Booster Bot

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Aiogram](https://img.shields.io/badge/aiogram-3.4.1+-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)

Telegram бот для накрутки часов в играх Steam с поддержкой управления тремя аккаунтами через удобный интерфейс с кнопками.

## 📁 Структура проекта

```
steam-hour-booster/
├── src/
│   ├── bot/                    # Telegram бот компоненты
│   │   ├── handlers.py         # Обработчики событий
│   │   ├── ui_manager.py       # Управление интерфейсом
│   │   ├── access_middleware.py # Middleware для доступа
│   │   └── states.py           # FSM состояния
│   ├── steam/                  # Steam клиент
│   │   └── steam_manager.py    # Управление Steam аккаунтами
│   └── config_manager.py       # Управление конфигурацией
├── config/
│   ├── config.ini.example      # Пример конфигурации
│   └── config.ini              # Ваша конфигурация (создается вами)
├── HourBooster.py              # Главный файл запуска
├── requirements.txt            # Зависимости
├── README.md                   # Документация
├── LICENSE                     # Лицензия MIT
└── .gitignore                  # Исключения для git
```

## 🚀 Возможности

- ⚡ Управление через inline кнопки (одно сообщение)
- 👥 Поддержка до 3 аккаунтов одновременно
- 🎮 Автоматическая накрутка часов для выбранных игр
- 🔐 Поддержка Steam Guard (мобильный и email)
- 📊 Статистика работы аккаунтов
- 🔄 Автоматическое обновление статуса

## 📋 Требования

- Python 3.8+
- aiogram 3.4.1+
- steam[client]

## 🛠️ Установка

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/soroka01/steam-hour-booster.git
cd steam-hour-booster
```

2. **Создайте виртуальное окружение:**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# или
source .venv/bin/activate  # Linux/Mac
```

3. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

4. **Настройте конфигурацию:**
```bash
# Скопируйте пример конфигурации
cp config/config.ini.example config/config.ini
# Отредактируйте config/config.ini своими данными
```

5. **Настройте `config/config.ini`:**
```ini
[telegram]
bot_token = ВАШ_ТОКЕН_БОТА
allowed_user_id = ВАШ_TELEGRAM_USER_ID

[account1]
username = логин_steam1
password = пароль1
games = 570,730,440 # ID игр через запятую

[account2]
username = логин_steam2
password = пароль2
games = 570,730,252490

[account3]
username = логин_steam3
password = пароль3
games = 570,730,1422450
```

6. **Запустите бота:**
```bash
python HourBooster.py
```

**Или используйте готовые скрипты:**
- Windows: `start.bat`
- Linux/Mac: `./start.sh`

## 🎯 Использование

1. Отправьте команду `/start` боту
2. Выберите аккаунт из списка
3. Нажмите "▶️ Запустить" для начала накрутки
4. Используйте "📊 Статистика" для проверки состояния
5. Нажмите "⏹️ Остановить" для завершения

## 🆕 Возможности aiogram

- Асинхронная обработка всех запросов
- Улучшенная система обработчиков
- Современный API для работы с inline клавиатурами
- Лучшая производительность и стабильность
- Автоматическое логирование событий

## 🔧 Настройка

### Получение токена Telegram бота:
1. Найдите [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте `/newbot` и следуйте инструкциям
3. Скопируйте полученный токен в `config/config.ini`

### Получение вашего Telegram User ID:
1. Найдите [@userinfobot](https://t.me/userinfobot) в Telegram
2. Отправьте `/start`
3. Скопируйте ваш ID в `config/config.ini`

### Получение ID игр Steam:
Найти ID игр можно на: [https://steamdb.info/search/](https://steamdb.info/search/)

### Настройка Steam Guard:
- Бот автоматически запросит код Steam Guard при первом входе
- Поддерживается как мобильное приложение, так и email

## ⚠️ Безопасность

- Никогда не делитесь своим `config/config.ini` файлом
- Используйте отдельные пароли для Steam аккаунтов
- Регулярно меняйте токен Telegram бота
- Файл `config/config.ini` автоматически исключен из git

## 🚀 Развертывание

### На сервере (Linux):
```bash
# Клонируйте репозиторий
git clone https://github.com/soroka01/steam-hour-booster.git
cd steam-hour-booster

# Создайте виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# Установите зависимости
pip install -r requirements.txt

# Настройте конфигурацию
cp config/config.ini.example config/config.ini
nano config/config.ini

# Запустите бота в фоне
nohup python HourBooster.py &
```

### Использование Docker:
```dockerfile
# Dockerfile (создайте самостоятельно)
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "HourBooster.py"]
```

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Создайте Pull Request

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## ⭐ Поддержка

Если проект оказался полезным, поставьте звезду ⭐!

## 🐛 Проблемы

Если возникают проблемы:
1. Убедитесь, что установлена aiogram версии 3.4.1+
2. Проверьте правильность настройки `config.ini`
3. Убедитесь, что все зависимости установлены
4. Проверьте подключение к интернету
5. Убедитесь, что Steam Guard настроен правильно
