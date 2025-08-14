from datetime import timedelta
from typing import List, Optional, TypedDict


class AuthConfigSchema(TypedDict, total=False):
    """TypedDict defining all possible authentication configuration options."""

    # Key and Identity Configuration
    PUBLIC_KEY_PATH: str
    PRIVATE_KEY_PATH: str
    PLATFORM_NAME: str

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

    RESERVED_USERNAMES: List[str]
    BASIC_ACCOUNT_SERIALIZER: str

    EMAIL_THREADING_ENABLED: bool
    BLACKLISTED_EMAILS: List[str]
    BLACKLISTED_PHONE_NUMBERS: List[str]
    ALLOWED_EMAIL_DOMAINS: List[str]
    VERIFICATION_EMAIL_SUBJECT: str
    PASSWORD_RESET_EMAIL_SUBJECT: str

    # Admin Interface
    ENABLE_ADMIN_PANEL: bool

    DISABLE_SIGNUP: bool
    SEND_PHONE_VERIFICATION_CODE_FUNC: str
    LOGIN_CODE_EMAIL_SUBJECT: str

    WEBAUTHN_DOMAIN: str  # required
    WEBAUTHN_RP_NAME: str  # required

    WEBAUTHN_ORIGIN: str  # required
