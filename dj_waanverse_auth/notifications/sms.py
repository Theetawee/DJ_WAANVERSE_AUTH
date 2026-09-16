from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def console_sms_sender(phone_number: str, code) -> None:
    """
    Default SMS sender. Logs the message instead of sending a real
    SMS — intended for local development. Override by pointing
    WAANVERSE_AUTH_CONFIG["SMS_SENDER"] at your own dotted path,
    e.g. "myproject.sms.send_via_twilio". The function must accept
    (phone_number: str, message: str) and return None.
    """

    logger.info("[SMS to %s] %s", phone_number, f"Your verification code is {code}.")
    print(f"[SMS to {phone_number}] Your verification code is {code}.")
