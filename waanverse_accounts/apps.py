# flake8: noqa

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "waanverse_accounts"
    label = "waanverse_accounts"
    verbose_name = "Waanverse Accounts"

    def ready(self):
        from .signals import log_user_logged_in_failed, log_user_logged_in_success
