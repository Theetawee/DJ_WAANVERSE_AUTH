from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Checks if required settings for dj-waanverse-auth are properly configured."

    def handle(self, *args, **kwargs):
        self._check_waanverse_auth_config()

        self._check_email_settings()

    def _check_waanverse_auth_config(self):
        """Check if the required WAANVERSE_AUTH_CONFIG settings are set."""
        required_keys = [
            "PUBLIC_KEY_PATH",
            "PRIVATE_KEY_PATH",
            "ACCESS_TOKEN_COOKIE_MAX_AGE",
            "REFRESH_TOKEN_COOKIE_MAX_AGE",
            "PASSWORD_CHANGED_FIELD_NAME",
            "PLATFORM_NAME",
        ]

        try:
            waanverse_config = getattr(settings, "WAANVERSE_AUTH_CONFIG", None)

            if not waanverse_config:
                raise ImproperlyConfigured("WAANVERSE_AUTH_CONFIG is not set.")

            for key in required_keys:
                if key not in waanverse_config:
                    self.stdout.write(
                        self.style.ERROR(f"{key} is missing in WAANVERSE_AUTH_CONFIG")
                    )

            self.stdout.write(
                self.style.SUCCESS("All WAANVERSE_AUTH_CONFIG settings are present.")
            )

        except ImproperlyConfigured as e:
            self.stdout.write(self.style.ERROR(str(e)))

    def _check_email_settings(self):
        """Check if the required email settings are configured."""
        required_email_keys = [
            "EMAIL_BACKEND",
            "EMAIL_HOST",
            "EMAIL_PORT",
            "EMAIL_USE_TLS",
            "EMAIL_HOST_USER",
            "EMAIL_HOST_PASSWORD",
        ]

        try:
            for key in required_email_keys:
                if not hasattr(settings, key):
                    self.stdout.write(
                        self.style.ERROR(f"{key} is missing in email settings.")
                    )

            self.stdout.write(self.style.SUCCESS("All email settings are present."))

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"An error occurred while checking email settings: {str(e)}"
                )
            )
