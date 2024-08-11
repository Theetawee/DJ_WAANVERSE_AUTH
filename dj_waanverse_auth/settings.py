from datetime import timedelta
from typing import List, Optional, TypedDict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class AccountConfigSchema(TypedDict, total=False):
    AUTH_METHODS: List[str]
    MFA_RECOVERY_CODES_COUNT: int
    ACCESS_TOKEN_COOKIE: str
    REFRESH_TOKEN_COOKIE: str
    COOKIE_PATH: str
    COOKIE_DOMAIN: Optional[str]
    COOKIE_SAMESITE_POLICY: str
    COOKIE_SECURE_FLAG: bool
    COOKIE_HTTP_ONLY_FLAG: bool
    MFA_COOKIE_NAME: str
    MFA_COOKIE_DURATION: timedelta
    USER_CLAIM_SERIALIZER_CLASS: str
    REGISTRATION_SERIALIZER_CLASS: str
    USERNAME_MIN_LENGTH: int
    DISALLOWED_USERNAMES: List[str]
    USER_DETAIL_SERIALIZER_CLASS: str
    ENABLE_EMAIL_ON_LOGIN: bool
    ENCRYPTION_KEY: Optional[str]
    CONFIRMATION_CODE_DIGITS: int
    PLATFORM_NAME: str
    EMAIL_VERIFICATION_CODE_DURATION: timedelta
    MFA_ISSUER_NAME: str
    BLACKLIST_TOKENS_ON_ROTATION: bool
    MFA_CODE_DIGITS: int
    MFA_EMAIL_ALERTS_ENABLED: bool
    PASSWORD_RESET_CODE_DURATION: timedelta
    PASSWORD_RESET_COOLDOWN_PERIOD: timedelta
    PASSWORD_RESET_MAX_ATTEMPTS: int


class AccountConfig:
    def __init__(self, settings_dict: AccountConfigSchema):
        self.AUTH_METHODS = settings_dict.get("AUTH_METHODS", ["username"])
        self.MFA_RECOVERY_CODES_COUNT = settings_dict.get("MFA_RECOVERY_CODES_COUNT", 10)
        self.ACCESS_TOKEN_COOKIE = settings_dict.get(
            "ACCESS_TOKEN_COOKIE", "access_token"
        )
        self.REFRESH_TOKEN_COOKIE = settings_dict.get(
            "REFRESH_TOKEN_COOKIE", "refresh_token"
        )
        self.COOKIE_PATH = settings_dict.get("COOKIE_PATH", "/")
        self.COOKIE_DOMAIN = settings_dict.get("COOKIE_DOMAIN", None)
        self.COOKIE_SAMESITE_POLICY = settings_dict.get("COOKIE_SAMESITE_POLICY", "Lax")
        self.COOKIE_SECURE_FLAG = settings_dict.get("COOKIE_SECURE_FLAG", False)
        self.COOKIE_HTTP_ONLY_FLAG = settings_dict.get("COOKIE_HTTP_ONLY_FLAG", True)
        self.MFA_COOKIE_NAME = settings_dict.get("MFA_COOKIE_NAME", "mfa_token")
        self.MFA_COOKIE_DURATION = settings_dict.get(
            "MFA_COOKIE_DURATION", timedelta(minutes=2)
        )
        self.USER_CLAIM_SERIALIZER_CLASS = settings_dict.get(
            "USER_CLAIM_SERIALIZER_CLASS",
            "dj_waanverse_auth.serializers.BasicAccountSerializer",
        )
        self.REGISTRATION_SERIALIZER_CLASS = settings_dict.get(
            "REGISTRATION_SERIALIZER_CLASS",
            "dj_waanverse_auth.serializers.SignupSerializer",
        )
        self.USERNAME_MIN_LENGTH = settings_dict.get("USERNAME_MIN_LENGTH", 4)
        self.DISALLOWED_USERNAMES = settings_dict.get(
            "DISALLOWED_USERNAMES", ["waanverse"]
        )
        self.USER_DETAIL_SERIALIZER_CLASS = settings_dict.get(
            "USER_DETAIL_SERIALIZER_CLASS",
            "dj_waanverse_auth.serializers.AccountSerializer",
        )
        self.ENABLE_EMAIL_ON_LOGIN = settings_dict.get("ENABLE_EMAIL_ON_LOGIN", False)
        self.ENCRYPTION_KEY = settings_dict.get("ENCRYPTION_KEY", None)
        self.CONFIRMATION_CODE_DIGITS = settings_dict.get("CONFIRMATION_CODE_DIGITS", 6)
        self.PLATFORM_NAME = settings_dict.get("PLATFORM_NAME", "Waanverse Accounts")
        self.EMAIL_VERIFICATION_CODE_DURATION = settings_dict.get(
            "EMAIL_VERIFICATION_CODE_DURATION", timedelta(minutes=10)
        )
        self.MFA_ISSUER_NAME = settings_dict.get(
            "MFA_ISSUER_NAME", "Waanverse Labs Inc."
        )
        self.BLACKLIST_TOKENS_ON_ROTATION = settings_dict.get(
            "BLACKLIST_TOKENS_ON_ROTATION", False
        )
        self.MFA_CODE_DIGITS = settings_dict.get("MFA_CODE_DIGITS", 6)
        self.MFA_EMAIL_ALERTS_ENABLED = settings_dict.get(
            "MFA_EMAIL_ALERTS_ENABLED", False
        )
        self.PASSWORD_RESET_CODE_DURATION = settings_dict.get(
            "PASSWORD_RESET_CODE_DURATION", timedelta(minutes=10)
        )
        self.PASSWORD_RESET_COOLDOWN_PERIOD = settings_dict.get(
            "PASSWORD_RESET_COOLDOWN_PERIOD", timedelta(minutes=5)
        )
        self.PASSWORD_RESET_MAX_ATTEMPTS = settings_dict.get(
            "PASSWORD_RESET_MAX_ATTEMPTS", 3
        )


# Merge user-provided settings with the default settings
USER_SETTINGS = getattr(settings, "WAANVERSE_AUTH", {})
accounts_config = AccountConfig({**AccountConfigSchema(), **USER_SETTINGS})

# Ensure email settings are configured if necessary
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
