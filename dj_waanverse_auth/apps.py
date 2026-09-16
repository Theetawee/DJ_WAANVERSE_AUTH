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
        from dj_waanverse_auth import (
            checks,
        )  # noqa: F401
