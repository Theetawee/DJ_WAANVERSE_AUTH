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
        self.disable_signup = config_dict.get("DISABLE_SIGNUP", False)

        self.authentication_identifiers = config_dict.get(
            "AUTHENTICATION_IDENTIFIERS", ["email", "phone"]
        )

        self.turnstile_enabled = config_dict.get("TURNSTILE_ENABLED", False)
        self.turnstile_secret_key = config_dict.get("TURNSTILE_SECRET_KEY", None)

        self.account_verification_email_subject = config_dict.get(
            "ACCOUNT_VERIFICATION_EMAIL_SUBJECT", "Verify your account"
        )

        self.sms_sender = config_dict.get("SMS_SENDER", None)
        self.activation_frontend_url = config_dict.get("ACTIVATION_FRONTEND_URL", None)

        self.verification_code_length = config_dict.get("VERIFICATION_CODE_LENGTH", 6)
        self.verification_code_ttl = config_dict.get(
            "VERIFICATION_CODE_TTL", timedelta(minutes=15)
        )
        self.verification_link_ttl = config_dict.get(
            "VERIFICATION_LINK_TTL", timedelta(minutes=15)
        )
        self.verification_max_attempts = config_dict.get("VERIFICATION_MAX_ATTEMPTS", 3)

        self.blacklisted_emails = config_dict.get("BLACKLISTED_EMAILS", [])
        self.allowed_email_domains = config_dict.get("ALLOWED_EMAIL_DOMAINS", [])
        self.blacklisted_email_domains = config_dict.get(
            "BLACKLISTED_EMAIL_DOMAINS", []
        )

        self.public_key_path = config_dict.get("PUBLIC_KEY_PATH")
        self.private_key_path = config_dict.get("PRIVATE_KEY_PATH")
        self.jwt_issuer = config_dict.get("JWT_ISSUER", "dj_waanverse_auth")
        self.access_token_lifetime = config_dict.get(
            "ACCESS_TOKEN_LIFETIME", timedelta(minutes=30)
        )
        self.refresh_token_lifetime = config_dict.get(
            "REFRESH_TOKEN_LIFETIME", timedelta(days=30)
        )
        self.access_token_cookie_name = config_dict.get(
            "ACCESS_TOKEN_COOKIE_NAME", "access_token"
        )
        self.refresh_token_cookie_name = config_dict.get(
            "REFRESH_TOKEN_COOKIE_NAME", "refresh_token"
        )

        self.cookie_path = config_dict.get("COOKIE_PATH", "/")
        self.cookie_domain = config_dict.get("COOKIE_DOMAIN", None)
        self.cookie_samesite = config_dict.get("COOKIE_SAMESITE_POLICY", "Lax")

        self.cookie_secure = config_dict.get("COOKIE_SECURE", False)

        self.trust_cloudflare_only = config_dict.get(
            "TRUST_CLOUDFLARE_ONLY", not settings.DEBUG
        )

        self.signup_serializer_class = config_dict.get(
            "SIGNUP_SERIALIZER_CLASS", "dj_waanverse_auth.serializers.SignupSerializer"
        )

        self.csrf_cookie_name = config_dict.get("CSRF_COOKIE_NAME", "csrftoken")
        self.enable_admin = config_dict.get("ENABLE_ADMIN_PANEL", False)


AUTH_CONFIG = getattr(settings, "WAANVERSE_AUTH_CONFIG", {})
auth_config = AuthConfig(AUTH_CONFIG)
