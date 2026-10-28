"""Steam messages (en)."""

MESSAGES = {
    # --- durations
    "steam.duration.minutes": "{count} min",
    "steam.duration.seconds": "{count} s",

    # --- alerts sent to the owner
    "steam.alert.blocked": "Steam blocked the game in this session: the account is playing on another device.",
    "steam.alert.left_game": "Steam reported that the game was closed.",
    "steam.alert.boost_paused": "{reason} Boost time tracking is paused; the connection is kept.",
    "steam.alert.playing_elsewhere": "The account is playing on another device. Boost time tracking is paused; the connection is kept.",
    "steam.alert.outage": "Steam has been unreachable for {duration}. Still reconnecting automatically (attempt {attempt}).",
    "steam.alert.restored": "Steam connection restored after {duration}.",
    "steam.alert.guard_needed": "Sign-in needs your input: {hint}. Open the account in the bot.",
    "steam.hint.mobile": "enter the Steam Guard code (or confirm in the Steam app)",
    "steam.hint.email": "enter the code from the Steam email",
    "steam.hint.other": "confirm the sign-in in the Steam app or via the link in the email",

    # --- session status / error texts
    "steam.session.connection_lost": "Connection to Steam lost. Reconnecting automatically.",
    "steam.session.no_connection": "Cannot reach Steam: {reason} Retrying.",
    "steam.session.failed": "Could not complete the sign-in or the Steam session. Please start it again.",
    "steam.session.kicked": (
        "Steam closed the session: the account signed in to Steam on another device or computer. "
        "Automatic reconnection is turned off so you are not kicked out of Steam. "
        "Start the account manually once it is free."
    ),
    "steam.session.account_denied": "Steam does not allow this account to sign in ({name}, code {code}).",
    "steam.session.token_rejected": "Steam rejected the token sign-in ({name}, code {code}).",
    "steam.session.playing_elsewhere": "Steam does not allow starting: the account is already playing on another device.",
    "steam.session.login_expired": "The sign-in confirmation timed out. Start the account again.",
    "steam.session.login_keeps_expiring": "The Steam sign-in confirmation request keeps expiring. Start the account again.",
    "steam.session.too_many_logins": (
        "Too many repeated password sign-ins: Steam seems to reject the token. "
        "Check the account and start it manually."
    ),
    "steam.session.auto_code_rejected": (
        "The automatic Steam Guard code was not accepted. Check shared_secret and the "
        "computer's clock, then enter the code manually."
    ),

    # --- reasons for a retry (shown inside steam.session.no_connection)
    "steam.retry.unavailable": "Steam is temporarily unavailable ({name}).",
    "steam.retry.logon_failed": "Connection to Steam failed during sign-in.",

    # --- log messages
    "steam.log.account_alert": "Steam account {account}: {message}",
    "steam.log.autostart": "Accounts autostarted after restart: {count}",
    "steam.log.session_error": "Steam session {account} error: {error}",
    "steam.log.close_failed": "Failed to close the Steam connection",
    "steam.log.connection_lost": "Steam account {account}: connection lost{detail}; reconnecting",
    "steam.log.connection_lost_detail": " (Steam: {code})",
    "steam.log.reconnect_failed": "Steam account {account}: reconnect attempt {attempt} failed: {reason}",
    "steam.log.token_expired": "Steam account {account}: token no longer accepted, signing in with the password",
    "steam.log.logon_failed": "Steam account {account} logon failed: {error}",
    "steam.log.session_active": "Steam session {account} is active",

    # --- authentication API
    "steam.auth.bad_credentials": "Steam did not accept the username or password in the modern API (code 5).",
    "steam.auth.bad_code": "Wrong Steam Guard code. Enter a new code.",
    "steam.auth.throttled": "Steam is limiting sign-in attempts. Try again later.",
    "steam.auth.request_expired": "The sign-in request expired. Start the account again.",
    "steam.auth.rejected": "Steam rejected the authorization (code {code}).",
    "steam.auth.unreachable": "Could not reach the Steam authorization API. Try again later.",
    "steam.auth.unsupported_confirmation": "Steam asked for an unsupported sign-in confirmation method.",
    "steam.auth.confirm_in_app": "Confirm the sign-in in the Steam app or via the link in the email.",

    # --- Steam Guard secrets
    "steam.guard.secret_not_base64": "shared_secret must be a base64 string (for example, from a maFile).",
    "steam.guard.secret_bad_length": "shared_secret has the wrong length. It is the \"shared_secret\" field of the maFile.",
    "steam.guard.mafile_unreadable": "This does not look like a maFile (it may be encrypted: an unencrypted file is required).",
    "steam.guard.mafile_not_object": "This does not look like a maFile.",
    "steam.guard.mafile_no_account": "The maFile has no account_name field.",
    "steam.guard.mafile_no_secret": "The maFile has no shared_secret field.",
    "steam.guard.empty": "Empty value: send the shared_secret or the contents of a maFile.",
    "steam.guard.otpauth_no_secret": "The otpauth link has no secret parameter.",
    "steam.guard.otpauth_unreadable": "Could not read the secret from the otpauth link.",
}
