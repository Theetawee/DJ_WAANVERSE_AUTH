# flake8: noqa

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class WaanverseAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dj_waanverse_auth"
    label = "dj_waanverse_auth"
    verbose_name = "Waanverse Auth"

    def ready(self):
        """
        Validate middleware configuration when the app is ready.
        This runs during Django's initialization process.
        """
        self.validate_middleware_settings()
        self.validate_required_settings()

    def validate_middleware_settings(self):
        """
        Ensures the DeviceAuthMiddleware is properly configured in settings.MIDDLEWARE
        """
        middleware_path = f"{self.name}.middleware.DeviceAuthMiddleware"

        if not hasattr(settings, "MIDDLEWARE"):
            raise ImproperlyConfigured(
                "MIDDLEWARE setting is not defined. "
                "Please configure your middleware settings properly."
            )

        if middleware_path not in settings.MIDDLEWARE:
            raise ImproperlyConfigured(
                f"DeviceAuthMiddleware is not found in your MIDDLEWARE setting. "
                f"Please add '{middleware_path}' to your MIDDLEWARE setting."
            )

    def validate_required_settings(self):
        """
        Validates other required settings are properly configured
        """
        pass
