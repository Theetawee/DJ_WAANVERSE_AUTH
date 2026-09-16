from __future__ import annotations

from django.utils.module_loading import import_string

from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.notifications.sms import console_sms_sender


def get_sms_sender():
    """
    Resolves the configured SMS sender, falling back to the console
    logger if none is set. Resolved fresh on every call — not cached
    at import time — so overriding via settings (including
    override_settings in tests) takes effect immediately.
    """

    sender_path = getattr(auth_config, "sms_sender", None)

    if not sender_path:
        return console_sms_sender

    return import_string(sender_path)


def send_verification_sms(phone_number: str, code: str) -> None:
    sender = get_sms_sender()
    sender(phone_number, code)
