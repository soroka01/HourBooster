"""Core messages (ru)."""

MESSAGES = {
    "core.storage.games.invalid": "Укажите Steam App ID положительными числами через запятую.",
    "core.storage.games.empty": "Добавьте хотя бы один Steam App ID.",
    "core.storage.games.too_many": "Для одного аккаунта можно указать не более 50 игр.",
    "core.storage.games.unreadable": "Не удалось прочитать список игр аккаунта из базы данных.",
    "core.storage.title.invalid": "Название аккаунта должно содержать от 1 до 48 символов.",
    "core.storage.username.invalid": "Логин Steam должен содержать от 1 до 128 символов.",
    "core.storage.password.invalid": "Пароль Steam должен содержать от 1 до 512 символов.",
    "core.storage.game_id.not_number": "Steam App ID должен быть числом.",
    "core.storage.game_id.not_positive": "Steam App ID должен быть положительным.",
    "core.storage.title.duplicate": "Аккаунт с таким названием уже существует.",
    "core.storage.account.create_failed": "Не удалось создать аккаунт.",
    "core.storage.account.update_failed": "Не удалось обновить аккаунт.",
    "core.storage.account.not_found": "Аккаунт не найден.",
    "core.storage.custom_game.invalid": "Название сторонней игры должно быть одной строкой до 64 символов.",
    "core.storage.field.unknown": "Неизвестное поле аккаунта.",
    "core.setup.not_interactive": "Запустите HourBooster.py --setup в интерактивной консоли.",
    "core.setup.prompt.language": "Язык (en/ru) [{current}]: ",
    "core.setup.prompt.token": "Telegram bot token: ",
    "core.setup.prompt.owner": "Telegram owner user ID: ",
    "core.setup.cancelled": "Настройка отменена.",
    "core.setup.invalid": "Укажите корректный токен Telegram и положительный user ID. Используйте --setup.",
    "core.main.setup_saved": "Настройки Telegram сохранены в SQLite.",
    "core.main.recovered": "Закрыто прерванных сессий после перезапуска: {count}",
    "core.main.commands_rejected": (
        "Telegram отклонил запрос настройки бота (404/401). "
        "Проверьте токен из @BotFather и сохраните его через HourBooster.py --setup."
    ),
    "core.main.started": "🎮 Steam Hour Booster запущен",
    "core.main.config_error": "Ошибка конфигурации: {error}",
}
