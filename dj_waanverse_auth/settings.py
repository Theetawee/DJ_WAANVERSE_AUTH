from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# Default settings for the package
DEFAULT_ACCOUNTS_CONFIG = {
    "AUTH_METHODS": ["username"],  # Available methods: ["username", "email", "phone"]
    "MFA_RECOVERY_CODES_COUNT": 2,
    "ACCESS_TOKEN_COOKIE": "access_token",
    "REFRESH_TOKEN_COOKIE": "refresh_token",
    "COOKIE_PATH": "/",
    "COOKIE_DOMAIN": None,
    "COOKIE_SAMESITE_POLICY": "Lax",
    "COOKIE_SECURE_FLAG": False,
    "COOKIE_HTTP_ONLY_FLAG": True,
    "MFA_COOKIE_NAME": "mfa_token",
    "MFA_COOKIE_DURATION": timedelta(minutes=2),
    "USER_CLAIM_SERIALIZER_CLASS": "dj_waanverse_auth.serializers.BasicAccountSerializer",
    "REGISTRATION_SERIALIZER_CLASS": "dj_waanverse_auth.serializers.SignupSerializer",
    "USERNAME_MIN_LENGTH": 4,
    "DISALLOWED_USERNAMES": ["waanverse"],
    "USER_DETAIL_SERIALIZER_CLASS": "dj_waanverse_auth.serializers.AccountSerializer",
    "ENABLE_EMAIL_ON_LOGIN": False,
    "ENCRYPTION_KEY": None,
    "CONFIRMATION_CODE_DIGITS": 6,
    "PLATFORM_NAME": "Waanverse Accounts",
    "EMAIL_VERIFICATION_CODE_DURATION": timedelta(minutes=10),
    "MFA_ISSUER_NAME": "Waanverse Labs Inc.",
    "BLACKLIST_TOKENS_ON_ROTATION": False,
    "MFA_CODE_DIGITS": 10,
    "MFA_EMAIL_ALERTS_ENABLED": False,
    "PASSWORD_RESET_CODE_DURATION": timedelta(minutes=10),
    "PASSWORD_RESET_COOLDOWN_PERIOD": timedelta(minutes=5),
    "PASSWORD_RESET_MAX_ATTEMPTS": 3,
}

# Merge user-provided settings with the default settings
USER_SETTINGS = getattr(settings, "WAANVERSE_AUTH", {})
accounts_config = {**DEFAULT_ACCOUNTS_CONFIG, **USER_SETTINGS}

required_email_settings = [
    "EMAIL_HOST",
    "EMAIL_PORT",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
    "EMAIL_USE_TLS",
]

for setting in required_email_settings:
    if not getattr(settings, setting, None):
        raise ImproperlyConfigured(
            f"Email setting '{setting}' is required but not configured."
        )
