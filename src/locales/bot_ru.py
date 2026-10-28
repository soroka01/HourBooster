"""Telegram bot messages (Russian)."""

MESSAGES = {
    # Command menu
    "bot.command.start": "🎮 Открыть аккаунты",
    "bot.command.menu": "🏠 Главное меню",
    "bot.command.cancel": "✖️ Отменить ввод",
    # Language toggle
    "bot.language.name.en": "English",
    "bot.language.name.ru": "Русский",
    "bot.button.language": "🌐 {name}",
    # Access middleware
    "bot.access.denied_callback": "🚫 Доступ только у владельца бота.",
    "bot.access.denied_message": "🚫 Этот бот настроен для личного использования владельцем.",
    # Durations and statuses
    "bot.duration.days_clock": "{days}д {hours:02d}:{minutes:02d}:{seconds:02d}",
    "bot.status.active": "🟢 Буст идёт",
    "bot.status.paused": "⏸️ Игра прервана",
    "bot.status.connecting": "🟡 Подключение",
    "bot.status.reconnecting": "🔄 Переподключение",
    "bot.status.awaiting_guard": "🔐 Нужен Steam Guard",
    "bot.status.awaiting_email": "📧 Нужен email-код",
    "bot.status.stopping": "🟠 Остановка",
    "bot.status.error": "🔴 Ошибка",
    "bot.status.stopped": "⚪ Остановлен",
    "bot.status.unknown": "⚪ Неизвестно",
    # Buttons
    "bot.button.add_account": "➕ Добавить аккаунт",
    "bot.button.import_guard": "🛡 Импорт Guard (maFile)",
    "bot.button.refresh": "🔄 Обновить",
    "bot.button.done": "✅ Готово",
    "bot.button.cancel": "✖️ Отменить",
    "bot.button.stop": "⏹️ Остановить",
    "bot.button.enter_code": "🔐 Ввести код",
    "bot.button.start": "🚀 Запустить",
    "bot.button.cancel_login": "❌ Отменить вход",
    "bot.button.stats": "📊 Статистика",
    "bot.button.edit": "✏️ Настроить",
    "bot.button.delete": "🗑 Удалить",
    "bot.button.all_accounts": "⬅️ Ко всем аккаунтам",
    "bot.button.title": "🏷 Название",
    "bot.button.username": "👤 Логин Steam",
    "bot.button.password": "🔑 Пароль Steam",
    "bot.button.guard_secret": "🛡 Steam Guard secret",
    "bot.button.clear_secret": "✖️ Убрать Guard secret",
    "bot.button.app_id": "🎯 Steam App ID",
    "bot.button.custom_game": "🎮 Кастомная игра",
    "bot.button.clear_custom": "✖️ Убрать кастомную игру",
    "bot.button.back": "⬅️ Назад",
    "bot.button.delete_confirm": "🗑 Да, удалить",
    "bot.button.cancel_back": "⬅️ Отмена",
    # Dashboard
    "bot.dashboard.header": "<b>🎮 Steam Hour Booster</b>\n<i>Один экран для ваших Steam-сессий</i>\n\n",
    "bot.dashboard.counts": "👥 Аккаунтов: <b>{total}</b>  •  🟢 На странице активно: <b>{active}</b>\n",
    "bot.dashboard.time": "⏱ На этой странице всего: <b>{duration}</b>\n",
    "bot.dashboard.empty": "\n✨ Пока нет аккаунтов. Добавьте первый — логин и пароль останутся только в локальной SQLite-базе.",
    "bot.dashboard.choose": "\n<b>Выберите аккаунт:</b>\n",
    "bot.dashboard.row_stats": "└ ⏱ {duration}  •  🎯 игр: {games}\n",
    # Account card
    "bot.account.login": "👤 Логин: <code>{username}</code>\n",
    "bot.account.status": "📡 Статус: <b>{status}</b>\n",
    "bot.account.reconnect_attempt": "🔄 Нет связи со Steam: попытка {attempt}",
    "bot.account.reconnect_down": ", простой {duration}",
    "bot.account.reconnect_next": " · следующая через {seconds} с",
    "bot.account.guard": "🛡 Steam Guard: <b>{mode}</b>\n",
    "bot.account.games_header": "🎯 Игры:\n",
    "bot.account.custom_game": "• <b>{name}</b> <i>(сторонняя игра)</i>\n",
    "bot.account.name_unavailable": "Название недоступно",
    "bot.account.total": "⏱ Всего буста: <b>{duration}</b>\n",
    "bot.account.session_active": "🟢 Текущая сессия: <b>{duration}</b>\n",
    "bot.account.session_idle": "💤 Текущая сессия: <b>не запущена</b>\n",
    "bot.account.completed": "🔢 Завершённых сессий: <b>{count}</b>\n",
    "bot.account.stats_note": "\n<i>Время начинает считаться только после успешного входа Steam.</i>",
    "bot.account.guard_confirmation": "\n🔐 Подтвердите запрос Steam Hour Booster в Steam или по ссылке из письма. Вход продолжится автоматически.",
    "bot.account.guard_mobile": "\n🔐 Введите код Steam Guard через кнопку ниже или подтвердите запрос Steam Hour Booster в приложении Steam.",
    "bot.account.guard_email": "\n📧 Введите код из письма Steam через кнопку ниже.",
    "bot.account.state": "\n\n⚠️ <b>Состояние:</b> {error}",
    "bot.guard.mode.auto": "авто",
    "bot.guard.mode.auto_saved": "авто (secret сохранён)",
    "bot.guard.mode.manual": "вручную",
    # Add-account form
    "bot.add.title": "<b>➕ Новый аккаунт · 1/4</b>\n\n🏷 Отправьте короткое название, например <code>Основной</code>.",
    "bot.add.title_invalid": "⚠️ Название должно содержать от 1 до 48 символов. Попробуйте ещё раз.",
    "bot.add.username": "<b>➕ Новый аккаунт · 2/4</b>\n\n👤 Отправьте логин Steam.",
    "bot.add.username_invalid": "⚠️ Логин должен содержать от 1 до 128 символов. Попробуйте ещё раз.",
    "bot.add.password": "<b>➕ Новый аккаунт · 3/4</b>\n\n🔑 Отправьте пароль Steam. Сообщение будет удалено, если Telegram разрешит это действие.",
    "bot.add.password_invalid": "⚠️ Пароль должен содержать от 1 до 512 символов. Попробуйте ещё раз.",
    "bot.add.games": "<b>➕ Новый аккаунт · 4/4</b>\n\n🎯 Отправьте Steam App ID через запятую, например <code>570,730,440</code>.",
    "bot.add.games_error": "⚠️ {error}\n\nОтправьте Steam App ID ещё раз.",
    # Guard import
    "bot.import.text": (
        "<b>🛡 Импорт Steam Guard</b>\n\n"
        "Отправьте один или несколько файлов <code>.maFile</code> документами (их создаёт steamguard-cli "
        "в папке <code>%APPDATA%\\steamguard-cli\\maFiles</code>). Файлы не должны быть зашифрованы. Бот сам сопоставит "
        "<code>account_name</code> из файла с логином Steam сохранённого аккаунта и включит для него "
        "автоматический Steam Guard. Сообщения будут удалены, если Telegram разрешит это действие."
    ),
    "bot.import.results_header": "<b>Результат:</b>",
    "bot.import.file_default": "файл",
    "bot.import.unreadable": "⚠️ {name}: не прочитан — {error}",
    "bot.import.no_account": "⚠️ нет аккаунта с логином {username}",
    "bot.import.document_required": "⚠️ Пришлите файл <code>.maFile</code> документом. Текст здесь не принимается.",
    # Settings menu and field prompts
    "bot.edit.menu": (
        "<b>✏️ Настройки: {title}</b>\n\n"
        "🛡 Steam Guard: {guard}\n\n"
        "Выберите поле. Пароль и secret никогда не показываются на экране."
    ),
    "bot.edit.prompt.title": "🏷 Отправьте новое название аккаунта.",
    "bot.edit.prompt.username": "👤 Отправьте новый логин Steam.",
    "bot.edit.prompt.password": "🔑 Отправьте новый пароль Steam. Сообщение будет удалено, если это возможно.",
    "bot.edit.prompt.games": "🎯 Отправьте Steam App ID через запятую, например <code>570,730</code>.",
    "bot.edit.prompt.shared_secret": (
        "🛡 Отправьте <code>shared_secret</code> из файла <code>.maFile</code> (steamguard-cli), весь текст файла "
        "<code>.maFile</code> или загрузите сам <code>.maFile</code> документом. "
        "Дальше бот сам будет вводить код Steam Guard при входе. "
        "Сообщение будет удалено, если Telegram разрешит это действие."
    ),
    "bot.edit.prompt.custom_game_name": "🎮 Отправьте название сторонней игры одной строкой (до 64 символов). Оно будет первым в списке игр Steam. Например: <code>Моя игра</code>.",
    "bot.edit.field": "<b>✏️ {title}</b>\n\n{prompt}",
    "bot.edit.error": "⚠️ {error}\n\nОтправьте значение ещё раз или отмените действие.",
    "bot.error.custom_game_empty": "Введите название или используйте кнопку «Убрать кастомную игру» в настройках.",
    "bot.error.mafile_other_login": "maFile принадлежит другому логину Steam, проверьте файл.",
    "bot.error.file_too_large": "Файл слишком большой для maFile (максимум 64 КБ).",
    "bot.error.download_failed": "Не удалось скачать файл из Telegram. Попробуйте ещё раз.",
    # Steam Guard code entry
    "bot.guard.empty": "⚠️ Код не может быть пустым. Отправьте код ещё раз.",
    "bot.guard.checking": "<b>⏳ Проверяем код Steam…</b>\n\nНе отправляйте его повторно, пока идёт проверка.",
    # Delete confirmation
    "bot.delete.confirm": (
        "<b>🗑 Удалить аккаунт {title}?</b>\n\n"
        "Будут удалены логин, пароль, список игр и сохранённая статистика. Это действие нельзя отменить."
    ),
    # Log messages
    "bot.log.refresh_failed": (
        "Не удалось обновить экран Telegram в чате {chat_id} ({error}). "
        "Повтор через {delay} с, попытка {attempt}. Steam-сессии не затронуты."
    ),
    "bot.log.refresh_restored": (
        "Обновление экрана Telegram в чате {chat_id} восстановлено после {failures} ошибок. "
        "Повторный вход в Steam не выполнялся."
    ),
    "bot.log.refresh_forbidden": (
        "Telegram запретил доступ к чату {chat_id}. Обновление экрана остановлено; "
        "Steam-сессии не затронуты."
    ),
    "bot.log.alert_waiting": "Уведомление об аккаунте {account} ожидает восстановления Telegram; повтор через {delay} с",
    "bot.log.alert_failed": "Не удалось отправить уведомление об аккаунте {account}: {error}",
    "bot.log.control_message_unavailable": "Служебное сообщение {message_id} недоступно: {error}",
    "bot.log.live_refresh_failed": "Не удалось обновить экран в чате {chat_id}",
    "bot.log.language_commands_failed": "Не удалось обновить меню команд бота после смены языка: {error}",
}
