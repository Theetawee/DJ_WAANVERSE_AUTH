from dataclasses import dataclass
from datetime import timedelta
from typing import List

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .types import AuthConfigSchema


@dataclass
class AuthConfig:
    """
    Authentication configuration class that validates and stores all auth-related settings.

    This class provides type checking, validation, and sensible defaults for all
    authentication configuration options.
    """

    def __init__(self, config_dict: AuthConfigSchema):
        # Security Settings
        self.public_key_path = config_dict.get("PUBLIC_KEY_PATH")
        self.private_key_path = config_dict.get("PRIVATE_KEY_PATH")
        self.user_id_claim = config_dict.get("USER_ID_CLAIM", "id")
        self.cloudflare_turnstile_secret = config_dict.get(
            "CLOUDFLARE_TURNSTILE_SECRET_KEY", None
        )

        # Cookie Settings
        self.access_token_cookie = config_dict.get(
            "ACCESS_TOKEN_COOKIE_NAME", "access_token"
        )
        self.refresh_token_cookie = config_dict.get(
            "REFRESH_TOKEN_COOKIE_NAME", "refresh_token"
        )
        self.cookie_path = config_dict.get("COOKIE_PATH", "/")
        self.cookie_domain = config_dict.get("COOKIE_DOMAIN", None)
        self.cookie_samesite = self._validate_samesite_policy(
            config_dict.get("COOKIE_SAMESITE_POLICY", "Lax")
        )
        self.cookie_secure = config_dict.get("COOKIE_SECURE", False)
        self.cookie_httponly = config_dict.get("COOKIE_HTTP_ONLY", True)
        self.access_token_cookie_max_age = config_dict.get(
            "ACCESS_TOKEN_COOKIE_MAX_AGE", timedelta(minutes=30)
        )
        self.refresh_token_cookie_max_age = config_dict.get(
            "REFRESH_TOKEN_COOKIE_MAX_AGE", timedelta(days=30)
        )

        # MFA Settings
        self.mfa_recovery_codes_count = self._validate_range(
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
        self.security_email_subject = config_dict.get(
            "SECURITY_EMAIL_SUBJECT", "Account security alert"
        )
        self.mfa_debug_code = config_dict.get("MFA_DEBUG_CODE", None)

        # User Settings
        self.username_min_length = self._validate_range(
            config_dict.get("USERNAME_MIN_LENGTH", 4),
            "USERNAME_MIN_LENGTH",
            min_value=3,
            max_value=5,
        )
        self.username_max_length = self._validate_range(
            config_dict.get("USERNAME_MAX_LENGTH", 20),
            "USERNAME_MAX_LENGTH",
            min_value=10,
            max_value=30,
        )
        self.reserved_usernames = set(
            config_dict.get(
                "RESERVED_USERNAMES", ["admin", "administrator", "root", "system"]
            )
        )

        # Serializer Classes
        self.basic_account_serializer_class = config_dict.get(
            "BASIC_ACCOUNT_SERIALIZER",
            "dj_waanverse_auth.serializers.base_serializers.BasicAccountSerializer",
        )
        self.registration_serializer = config_dict.get(
            "REGISTRATION_SERIALIZER",
            "dj_waanverse_auth.serializers.signup_serializers.SignupSerializer",
        )
        self.update_account_serializer = config_dict.get(
            "UPDATE_ACCOUNT_SERIALIZER",
            "dj_waanverse_auth.serializers.authorization_serializer.UpdateAccountSerializer",
        )

        # Email Settings
        self.email_verification_code_length = self._validate_range(
            config_dict.get("EMAIL_VERIFICATION_CODE_LENGTH", 6),
            "EMAIL_VERIFICATION_CODE_LENGTH",
            min_value=6,
            max_value=12,
        )
        self.email_verification_code_is_alphanumeric = config_dict.get(
            "EMAIL_VERIFICATION_CODE_IS_ALPHANUMERIC", False
        )
        self.email_security_notifications_enabled = config_dict.get(
            "EMAIL_SECURITY_NOTIFICATIONS_ENABLED", True
        )
        self.email_threading_enabled = config_dict.get("EMAIL_THREADING_ENABLED", True)
        self.blacklisted_emails = config_dict.get("BLACKLISTED_EMAILS", [])
        self.blacklisted_phone_numbers = config_dict.get(
            "BLACKLISTED_PHONE_NUMBERS", []
        )
        self.disposable_email_domains = config_dict.get("DISPOSABLE_EMAIL_DOMAINS", [])
        self.email_batch_size = config_dict.get("EMAIL_BATCH_SIZE", 50)
        self.email_retry_attempts = config_dict.get("EMAIL_RETRY_ATTEMPTS", 3)
        self.email_retry_delay = config_dict.get("EMAIL_RETRY_DELAY", 5)
        self.email_max_recipients = config_dict.get("EMAIL_MAX_RECIPIENTS", 50)
        self.email_thread_pool_size = config_dict.get("EMAIL_THREAD_POOL_SIZE", 5)
        self.verification_email_subject = config_dict.get(
            "VERIFICATION_EMAIL_SUBJECT", "Verify your email address"
        )
        self.verification_email_code_expiry_in_minutes = config_dict.get(
            "VERIFICATION_EMAIL_CODE_EXPIRATION_TIME_MINUTES", 15
        )
        self.phone_number_verification_serializer = config_dict.get(
            "PHONE_NUMBER_VERIFICATION_SERIALIZER",
            "dj_waanverse_auth.serializers.signup_serializers.PhoneNumberVerificationSerializer",
        )
        self.login_alert_email_subject = config_dict.get(
            "LOGIN_ALERT_EMAIL_SUBJECT", "New login alert"
        )
        self.password_reset_expiry_in_minutes = config_dict.get(
            "PASSWORD_RESET_CODE_EXPIRY_IN_MINUTES", 10
        )
        self.password_reset_code_length = self._validate_range(
            config_dict.get("PASSWORD_RESET_CODE_LENGTH", 6),
            "PASSWORD_RESET_CODE_LENGTH",
            min_value=6,
            max_value=12,
        )
        self.password_reset_email_subject = config_dict.get(
            "PASSWORD_RESET_EMAIL_SUBJECT", "Password reset request"
        )

        # Admin Interface
        self.enable_admin = config_dict.get("ENABLE_ADMIN_PANEL", False)
        self.use_unfold = config_dict.get("USE_UNFOLD_THEME", False)

        # Branding
        self.platform_name = config_dict.get("PLATFORM_NAME", "Authentication Service")
        self.platform_address = config_dict.get("PLATFORM_ADDRESS", "123 Main St.")
        self.platform_contact_email = config_dict.get(
            "PLATFORM_CONTACT_EMAIL", "support@waanverse.com"
        )

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
