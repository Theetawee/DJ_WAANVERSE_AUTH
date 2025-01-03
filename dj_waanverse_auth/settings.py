from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional, TypedDict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class AuthConfigSchema(TypedDict, total=False):
    """TypedDict defining all possible authentication configuration options."""

    # Security Settings
    AUTH_METHODS: List[str]
    PUBLIC_KEY_PATH: Optional[str]
    PRIVATE_KEY_PATH: Optional[str]
    HEADER_NAME: str
    USER_ID_CLAIM: str
    TOKEN_CACHE_TTL: int
    CACHE_PREFIX: str
    PASSWORD_CHANGED_FIELD_NAME: str

    # Cookie Configuration
    ACCESS_TOKEN_COOKIE_NAME: str
    REFRESH_TOKEN_COOKIE_NAME: str
    COOKIE_PATH: str
    COOKIE_DOMAIN: Optional[str]
    COOKIE_SAMESITE_POLICY: str
    COOKIE_SECURE: bool
    COOKIE_HTTP_ONLY: bool
    ACCESS_TOKEN_COOKIE_MAX_AGE: int
    REFRESH_TOKEN_COOKIE_MAX_AGE: int

    # Multi-Factor Authentication
    MFA_ENABLED: bool
    MFA_TOKEN_COOKIE_NAME: str
    MFA_TOKEN_DURATION: timedelta
    MFA_RECOVERY_CODE_COUNT: int
    MFA_ISSUER_NAME: str
    MFA_CODE_LENGTH: int
    MFA_EMAIL_NOTIFICATIONS: bool

    # User Configuration
    USERNAME_MIN_LENGTH: int
    RESERVED_USERNAMES: List[str]

    # Serializer Classes
    USER_CLAIMS_SERIALIZER: str
    REGISTRATION_SERIALIZER: str
    USER_DETAIL_SERIALIZER: str

    # Email Settings
    EMAIL_VERIFICATION_ENABLED: bool
    EMAIL_VERIFICATION_CODE_LENGTH: int
    EMAIL_VERIFICATION_CODE_EXPIRY: int  # minutes
    EMAIL_NOTIFICATIONS_ENABLED: bool
    EMAIL_THREADING_ENABLED: bool
    AUTO_RESEND_VERIFICATION_EMAIL: bool

    # Password Reset
    PASSWORD_RESET_CODE_EXPIRY: timedelta
    PASSWORD_RESET_COOLDOWN: int  # minutes

    # Admin Interface
    ENABLE_ADMIN_PANEL: bool
    USE_UNFOLD_THEME: bool

    # Branding
    PLATFORM_NAME: str


@dataclass
class AuthConfig:
    """
    Authentication configuration class that validates and stores all auth-related settings.

    This class provides type checking, validation, and sensible defaults for all
    authentication configuration options.
    """

    def __init__(self, config_dict: AuthConfigSchema):
        # Security Settings
        self.auth_methods = self._validate_auth_methods(
            config_dict.get("AUTH_METHODS", ["username"])
        )
        self.public_key_path = config_dict.get("PUBLIC_KEY_PATH")
        self.private_key_path = config_dict.get("PRIVATE_KEY_PATH")
        self.header_name = config_dict.get("HEADER_NAME", "X-Auth-Token")
        self.user_id_claim = config_dict.get("USER_ID_CLAIM", "user_id")
        self.token_cache_ttl = config_dict.get("TOKEN_CACHE_TTL", 300)
        self.cache_prefix = config_dict.get("CACHE_PREFIX", "jwt_token_")
        self.password_changed_field_name = config_dict.get(
            "PASSWORD_CHANGED_FIELD_NAME", "password_changed_at"
        )

        # Cookie Settings
        self.access_token_cookie = config_dict.get(
            "ACCESS_TOKEN_COOKIE_NAME", "access_token"
        )
        self.refresh_token_cookie = config_dict.get(
            "REFRESH_TOKEN_COOKIE_NAME", "refresh_token"
        )
        self.cookie_path = config_dict.get("COOKIE_PATH", "/")
        self.cookie_domain = config_dict.get("COOKIE_DOMAIN")
        self.cookie_samesite = self._validate_samesite_policy(
            config_dict.get("COOKIE_SAMESITE_POLICY", "Lax")
        )
        self.cookie_secure = config_dict.get("COOKIE_SECURE", False)
        self.cookie_httponly = config_dict.get("COOKIE_HTTP_ONLY", True)
        self.access_token_cookie_max_age = config_dict.get(
            "ACCESS_TOKEN_COOKIE_MAX_AGE"
        )
        self.refresh_token_cookie_max_age = config_dict.get(
            "REFRESH_TOKEN_COOKIE_MAX_AGE"
        )

        # MFA Settings
        self.mfa_enabled = config_dict.get("MFA_ENABLED", True)
        self.mfa_token_cookie = config_dict.get("MFA_TOKEN_COOKIE_NAME", "mfa_token")
        self.mfa_token_duration = config_dict.get(
            "MFA_TOKEN_DURATION", timedelta(minutes=2)
        )
        self.mfa_recovery_codes = self._validate_range(
            config_dict.get("MFA_RECOVERY_CODE_COUNT", 10),
            "MFA_RECOVERY_CODE_COUNT",
            min_value=5,
            max_value=20,
        )
        self.mfa_issuer = config_dict.get("MFA_ISSUER_NAME", "Authentication Service")
        self.mfa_code_length = self._validate_range(
            config_dict.get("MFA_CODE_LENGTH", 6),
            "MFA_CODE_LENGTH",
            min_value=6,
            max_value=8,
        )
        self.mfa_email_notifications = config_dict.get("MFA_EMAIL_NOTIFICATIONS", True)

        # User Settings
        self.username_min_length = self._validate_range(
            config_dict.get("USERNAME_MIN_LENGTH", 4),
            "USERNAME_MIN_LENGTH",
            min_value=3,
            max_value=32,
        )
        self.reserved_usernames = set(
            config_dict.get(
                "RESERVED_USERNAMES", ["admin", "administrator", "root", "system"]
            )
        )

        # Serializer Classes
        self.user_claims_serializer = config_dict.get(
            "USER_CLAIMS_SERIALIZER", "auth.serializers.BasicUserClaimsSerializer"
        )
        self.registration_serializer = config_dict.get(
            "REGISTRATION_SERIALIZER", "auth.serializers.UserRegistrationSerializer"
        )
        self.user_detail_serializer = config_dict.get(
            "USER_DETAIL_SERIALIZER", "auth.serializers.UserDetailSerializer"
        )

        # Email Settings
        self.email_verification_enabled = config_dict.get(
            "EMAIL_VERIFICATION_ENABLED", True
        )
        self.email_verification_code_length = self._validate_range(
            config_dict.get("EMAIL_VERIFICATION_CODE_LENGTH", 6),
            "EMAIL_VERIFICATION_CODE_LENGTH",
            min_value=6,
            max_value=12,
        )
        self.email_verification_expiry = config_dict.get(
            "EMAIL_VERIFICATION_CODE_EXPIRY", 10
        )
        self.email_notifications_enabled = config_dict.get(
            "EMAIL_NOTIFICATIONS_ENABLED", True
        )
        self.email_threading_enabled = config_dict.get("EMAIL_THREADING_ENABLED", True)
        self.auto_resend_verification = config_dict.get(
            "AUTO_RESEND_VERIFICATION_EMAIL", False
        )

        # Password Reset Settings
        self.password_reset_expiry = config_dict.get(
            "PASSWORD_RESET_CODE_EXPIRY", timedelta(minutes=10)
        )
        self.password_reset_cooldown = config_dict.get("PASSWORD_RESET_COOLDOWN", 5)

        # Admin Interface
        self.enable_admin = config_dict.get("ENABLE_ADMIN_PANEL", False)
        self.use_unfold = config_dict.get("USE_UNFOLD_THEME", False)

        # Branding
        self.platform_name = config_dict.get("PLATFORM_NAME", "Authentication Service")

        # Validate configuration
        self._validate_configuration()

    @staticmethod
    def _validate_auth_methods(methods: List[str]) -> List[str]:
        """Validate authentication methods."""
        valid_methods = {"username", "email", "phone"}
        invalid_methods = set(methods) - valid_methods
        if invalid_methods:
            raise ImproperlyConfigured(
                f"Invalid authentication methods: {invalid_methods}. "
                f"Valid options are: {valid_methods}"
            )
        return methods

    @staticmethod
    def _validate_samesite_policy(policy: str) -> str:
        """Validate SameSite cookie policy."""
        valid_policies = {"Strict", "Lax", "None"}
        if policy not in valid_policies:
            raise ImproperlyConfigured(
                f"Invalid SameSite policy: {policy}. "
                f"Valid options are: {valid_policies}"
            )
        return policy

    @staticmethod
    def _validate_range(
        value: int, setting_name: str, min_value: int, max_value: int
    ) -> int:
        """Validate numeric range for configuration values."""
        if not min_value <= value <= max_value:
            raise ImproperlyConfigured(
                f"{setting_name} must be between {min_value} and {max_value}, "
                f"got {value}"
            )
        return value

    def _validate_configuration(self) -> None:
        """Validate the complete configuration."""
        if self.email_verification_enabled or self.email_notifications_enabled:
            self._validate_email_settings()

        if self.use_unfold:
            self._validate_unfold_installation()

    @staticmethod
    def _validate_email_settings() -> None:
        """Validate required email settings."""
        required_settings = [
            "EMAIL_HOST",
            "EMAIL_PORT",
            "EMAIL_HOST_USER",
            "EMAIL_HOST_PASSWORD",
            "EMAIL_USE_TLS",
        ]

        missing_settings = [
            setting
            for setting in required_settings
            if not getattr(settings, setting, None)
        ]

        if missing_settings:
            raise ImproperlyConfigured(
                "Missing required email settings: "
                f"{', '.join(missing_settings)}. "
                "See https://docs.djangoproject.com/en/stable/topics/email/"
            )

    @staticmethod
    def _validate_unfold_installation() -> None:
        """Validate Unfold theme installation."""
        if "unfold" not in settings.INSTALLED_APPS:
            raise ImproperlyConfigured(
                "'unfold' must be in INSTALLED_APPS when USE_UNFOLD_THEME is True"
            )


AUTH_CONFIG = getattr(settings, "WAANVERSE_AUTH_CONFIG", {})
auth_config = AuthConfig(AUTH_CONFIG)
