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
        self.validate_required_settings()

    def validate_required_settings(self):
        """
        Validates other required settings are properly configured
        """
        pass
