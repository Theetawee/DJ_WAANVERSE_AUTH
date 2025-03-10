from datetime import timedelta
from typing import List, Optional, TypedDict


class AuthConfigSchema(TypedDict, total=False):
    """TypedDict defining all possible authentication configuration options."""

    # Key and Identity Configuration
    PUBLIC_KEY_PATH: str
    PRIVATE_KEY_PATH: str
    USER_ID_CLAIM: str
    CLOUDFLARE_TURNSTILE_SECRET_KEY: str

    # Cookie Configuration
    ACCESS_TOKEN_COOKIE_NAME: str
    REFRESH_TOKEN_COOKIE_NAME: str
    COOKIE_PATH: str
    COOKIE_DOMAIN: Optional[str]
    COOKIE_SAMESITE_POLICY: str
    COOKIE_SECURE: bool
    COOKIE_HTTP_ONLY: bool
    ACCESS_TOKEN_COOKIE_MAX_AGE: timedelta
    REFRESH_TOKEN_COOKIE_MAX_AGE: timedelta

    # Multi-Factor Authentication (MFA)
    MFA_RECOVERY_CODE_COUNT: int
    MFA_ISSUER_NAME: str
    MFA_CODE_LENGTH: int
    MFA_DEBUG_CODE: str  # Optional debug code for development mode
    SECURITY_EMAIL_SUBJECT: str
    EMAIL_SECURITY_NOTIFICATIONS_ENABLED: bool

    # User Configuration
    USERNAME_MIN_LENGTH: int
    RESERVED_USERNAMES: List[str]
    USERNAME_MAX_LENGTH: int

    # Email Settings
    EMAIL_VERIFICATION_CODE_LENGTH: int
    EMAIL_VERIFICATION_CODE_IS_ALPHANUMERIC: bool
    EMAIL_THREADING_ENABLED: bool
    BLACKLISTED_EMAILS: List[str]
    BLACKLISTED_PHONE_NUMBERS: List[str]
    DISPOSABLE_EMAIL_DOMAINS: List[str]
    EMAIL_BATCH_SIZE: int
    EMAIL_RETRY_ATTEMPTS: int
    EMAIL_RETRY_DELAY: int
    EMAIL_MAX_RECIPIENTS: int
    EMAIL_THREAD_POOL_SIZE: int
    VERIFICATION_EMAIL_SUBJECT: str
    VERIFICATION_EMAIL_CODE_EXPIRATION_TIME_MINUTES: int  # in minutes
    PHONE_NUMBER_VERIFICATION_SERIALIZER: str
    # Password Reset
    PASSWORD_RESET_CODE_EXPIRY_IN_MINUTES: int  # in minutes
    PASSWORD_RESET_EMAIL_SUBJECT: str
    PASSWORD_RESET_CODE_LENGTH: int

    # Admin Interface
    ENABLE_ADMIN_PANEL: bool
    USE_UNFOLD_THEME: bool

    # Platform Branding
    PLATFORM_NAME: str
    PLATFORM_ADDRESS: str
    PLATFORM_CONTACT_EMAIL: str

    # Serializer Classes
    BASIC_ACCOUNT_SERIALIZER: str
    REGISTRATION_SERIALIZER: str
    UPDATE_ACCOUNT_SERIALIZER: str
