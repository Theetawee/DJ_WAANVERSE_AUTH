from datetime import timedelta
from typing import List, Optional, TypedDict


class AuthConfigSchema(TypedDict, total=False):
    """TypedDict defining all possible authentication configuration options."""

    DISABLE_SIGNUP: bool
    AUTHENTICATION_IDENTIFIERS: List[str]
    TURNSTILE_ENABLED: bool
    TURNSTILE_SECRET_KEY: str

    ACCOUNT_VERIFICATION_EMAIL_SUBJECT: str
    SMS_SENDER: str
    FRONTEND_URL: str

    VERIFICATION_CODE_LENGTH: int
    VERIFICATION_CODE_TTL: timedelta
    VERIFICATION_LINK_TTL: timedelta
    VERIFICATION_MAX_ATTEMPTS: int

    BLACKLISTED_EMAILS: List[str]
    ALLOWED_EMAIL_DOMAINS: List[str]
    BLACKLISTED_EMAIL_DOMAINS: List[str]

    PUBLIC_KEY_PATH: str
    PRIVATE_KEY_PATH: str

    JWT_ISSUER: str
    ACCESS_TOKEN_LIFETIME: timedelta
    REFRESH_TOKEN_LIFETIME: timedelta

    ACCESS_TOKEN_COOKIE_NAME: str
    REFRESH_TOKEN_COOKIE_NAME: str

    COOKIE_PATH: str
    COOKIE_DOMAIN: Optional[str]
    COOKIE_SAMESITE_POLICY: str
    COOKIE_SECURE: bool

    TRUST_CLOUDFLARE_ONLY: bool

    SIGNUP_SERIALIZER: str

    # The rest....

    # Key and Identity Configuration
    PLATFORM_NAME: str

    # Cookie Configuration
    LOGIN_CODE_EMAIL_SUBJECT: str
    SIGNUP_CODE_EMAIL_SUBJECT: str

    BASIC_ACCOUNT_SERIALIZER: str

    # Admin Interface
    ENABLE_ADMIN_PANEL: bool

    IS_TESTING: bool
    TESTING_EMAIL_ADDRESSES: List[str]

    WEBAUTHN_DOMAIN: str
    WEBAUTHN_RP_NAME: str
    WEBAUTHN_ORIGIN: str

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    GOOGLE_REDIRECT_URI: str

    AUTH_FRONTEND_URL: str
