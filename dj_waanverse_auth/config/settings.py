from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings

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
        self.platform_name = config_dict.get("PLATFORM_NAME")

        # Cookie Settings
        self.access_token_cookie = config_dict.get(
            "ACCESS_TOKEN_COOKIE_NAME", "access_token"
        )
        self.refresh_token_cookie = config_dict.get(
            "REFRESH_TOKEN_COOKIE_NAME", "refresh_token"
        )
        self.cookie_path = config_dict.get("COOKIE_PATH", "/")
        self.cookie_domain = config_dict.get("COOKIE_DOMAIN", None)
        self.cookie_samesite = config_dict.get("COOKIE_SAMESITE_POLICY", "Lax")

        self.cookie_secure = config_dict.get("COOKIE_SECURE", False)
        self.cookie_httponly = config_dict.get("COOKIE_HTTP_ONLY", True)
        self.access_token_cookie_max_age = config_dict.get(
            "ACCESS_TOKEN_COOKIE_MAX_AGE", timedelta(minutes=30)
        )
        self.refresh_token_cookie_max_age = config_dict.get(
            "REFRESH_TOKEN_COOKIE_MAX_AGE", timedelta(days=30)
        )

        self.basic_account_serializer_class = config_dict.get(
            "BASIC_ACCOUNT_SERIALIZER",
            "dj_waanverse_auth.serializers.BasicAccountSerializer",
        )

        self.blacklisted_emails = config_dict.get("BLACKLISTED_EMAILS", [])
        self.allowed_email_domains = config_dict.get("ALLOWED_EMAIL_DOMAINS", [])

        # Admin Interface
        self.enable_admin = config_dict.get("ENABLE_ADMIN_PANEL", False)

        self.disable_signup = config_dict.get("DISABLE_SIGNUP", False)

        self.login_code_email_subject = config_dict.get(
            "LOGIN_CODE_EMAIL_SUBJECT", "Login code"
        )

        self.webauthn_domain = config_dict.get("WEBAUTHN_DOMAIN", None)
        self.webauthn_rp_name = config_dict.get("WEBAUTHN_RP_NAME", None)
        self.webauthn_origin = config_dict.get("WEBAUTHN_ORIGIN", None)

        self.is_testing = config_dict.get("IS_TESTING", False)


AUTH_CONFIG = getattr(settings, "WAANVERSE_AUTH_CONFIG", {})
auth_config = AuthConfig(AUTH_CONFIG)
