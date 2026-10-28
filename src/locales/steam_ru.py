"""Steam messages (ru)."""

MESSAGES = {
    # --- durations
    "steam.duration.minutes": "{count} мин",
    "steam.duration.seconds": "{count} с",

    # --- alerts sent to the owner
    "steam.alert.blocked": "Steam заблокировал игру в этой сессии: аккаунт играет на другом устройстве.",
    "steam.alert.left_game": "Steam сообщил о выходе из игры.",
    "steam.alert.boost_paused": "{reason} Учёт буста приостановлен; подключение сохранено.",
    "steam.alert.playing_elsewhere": "Аккаунт играет на другом устройстве. Учёт буста приостановлен; подключение сохранено.",
    "steam.alert.outage": "Нет связи со Steam уже {duration}. Продолжаю переподключаться автоматически (попытка {attempt}).",
    "steam.alert.restored": "Соединение со Steam восстановлено через {duration}.",
    "steam.alert.guard_needed": "Для входа {hint}. Откройте аккаунт в боте.",
    "steam.hint.mobile": "нужен код Steam Guard (или подтверждение в приложении Steam)",
    "steam.hint.email": "нужен код из письма Steam",
    "steam.hint.other": "подтвердите вход в приложении Steam или по ссылке из письма",

    # --- session status / error texts
    "steam.session.connection_lost": "Соединение со Steam потеряно. Переподключаюсь автоматически.",
    "steam.session.no_connection": "Нет связи со Steam: {reason} Повторяю попытки.",
    "steam.session.failed": "Не удалось завершить вход или Steam-сессию. Повторите запуск.",
    "steam.session.kicked": (
        "Steam закрыл сессию: аккаунт вошёл в Steam на другом устройстве или компьютере. "
        "Автопереподключение отключено, чтобы не вытеснять вас из Steam. "
        "Запустите аккаунт вручную, когда он освободится."
    ),
    "steam.session.account_denied": "Steam не пускает этот аккаунт ({name}, код {code}).",
    "steam.session.token_rejected": "Steam отклонил вход по токену ({name}, код {code}).",
    "steam.session.playing_elsewhere": "Steam не разрешает запуск: аккаунт уже играет на другом устройстве.",
    "steam.session.login_expired": "Время подтверждения входа истекло. Запустите аккаунт заново.",
    "steam.session.login_keeps_expiring": "Запрос подтверждения входа в Steam постоянно истекает. Запустите аккаунт заново.",
    "steam.session.too_many_logins": (
        "Слишком частые повторные входы по паролю: Steam, похоже, не принимает токен. "
        "Проверьте аккаунт и запустите его вручную."
    ),
    "steam.session.auto_code_rejected": (
        "Автоматический код Steam Guard не принят. Проверьте shared_secret и время "
        "на компьютере; введите код вручную."
    ),

    # --- reasons for a retry (shown inside steam.session.no_connection)
    "steam.retry.unavailable": "Steam временно недоступен ({name}).",
    "steam.retry.logon_failed": "Сбой соединения со Steam при входе.",

    # --- log messages
    "steam.log.account_alert": "Steam-аккаунт {account}: {message}",
    "steam.log.autostart": "Автозапуск аккаунтов после перезапуска: {count}",
    "steam.log.session_error": "Ошибка Steam-сессии {account}: {error}",
    "steam.log.close_failed": "Не удалось закрыть Steam-соединение",
    "steam.log.connection_lost": "Steam-аккаунт {account}: соединение потеряно{detail}; переподключение",
    "steam.log.connection_lost_detail": " (Steam: {code})",
    "steam.log.reconnect_failed": "Steam-аккаунт {account}: попытка переподключения {attempt} не удалась: {reason}",
    "steam.log.token_expired": "Steam-аккаунт {account}: токен больше не принимается, вход по паролю",
    "steam.log.logon_failed": "Сбой входа Steam-аккаунта {account}: {error}",
    "steam.log.session_active": "Steam-сессия {account} активна",

    # --- authentication API
    "steam.auth.bad_credentials": "Steam не принял логин или пароль в современном API (код 5).",
    "steam.auth.bad_code": "Неверный код Steam Guard. Введите новый код.",
    "steam.auth.throttled": "Steam ограничил попытки входа. Повторите позже.",
    "steam.auth.request_expired": "Запрос входа истёк. Запустите аккаунт заново.",
    "steam.auth.rejected": "Steam отклонил авторизацию (код {code}).",
    "steam.auth.unreachable": "Не удалось связаться с API авторизации Steam. Повторите позже.",
    "steam.auth.unsupported_confirmation": "Steam запросил неподдерживаемый способ подтверждения входа.",
    "steam.auth.confirm_in_app": "Подтвердите вход в приложении Steam или по ссылке из письма.",

    # --- Steam Guard secrets
    "steam.guard.secret_not_base64": "shared_secret должен быть строкой base64 (например, из maFile).",
    "steam.guard.secret_bad_length": "shared_secret имеет неверную длину. Это поле «shared_secret» из maFile.",
    "steam.guard.mafile_unreadable": "Файл не похож на maFile (возможно, он зашифрован: нужен файл без шифрования).",
    "steam.guard.mafile_not_object": "Файл не похож на maFile.",
    "steam.guard.mafile_no_account": "В maFile нет поля account_name.",
    "steam.guard.mafile_no_secret": "В maFile нет поля shared_secret.",
    "steam.guard.empty": "Пустое значение: пришлите shared_secret или содержимое maFile.",
    "steam.guard.otpauth_no_secret": "В otpauth-ссылке нет параметра secret.",
    "steam.guard.otpauth_unreadable": "Не удалось прочитать secret из otpauth-ссылки.",
}
