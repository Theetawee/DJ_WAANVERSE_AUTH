from __future__ import annotations

import logging

import requests
from django.core.exceptions import ImproperlyConfigured

from dj_waanverse_auth import settings as auth_config

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def verify_turnstile_token(token: str, remote_ip: str | None = None) -> bool:
    """
    Verify a Cloudflare Turnstile token against Cloudflare's siteverify
    endpoint.

    Returns False on any failure to verify — including network errors,
    timeouts, or a missing secret key — so verification fails closed
    rather than silently letting requests through.
    """

    if not auth_config.turnstile_enabled:
        return True

    if not token:
        return False

    secret_key = auth_config.turnstile_secret_key

    if not secret_key:
        raise ImproperlyConfigured(
            "TURNSTILE_SECRET_KEY must be set when ENABLE_TURNSTILE is True."
        )

    payload = {"secret": secret_key, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        response = requests.post(TURNSTILE_VERIFY_URL, data=payload, timeout=5)
        response.raise_for_status()
    except requests.RequestException:
        logger.warning("Turnstile verification request failed.", exc_info=True)
        return False

    data = response.json()
    return bool(data.get("success"))
