from __future__ import annotations
from dj_waanverse_auth import settings as auth_config
import hmac
import secrets

CSRF_COOKIE_NAME = auth_config.csrf_cookie_name
CSRF_HEADER_NAME = "HTTP_X_CSRF_TOKEN"  # client sends: X-CSRF-Token


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def get_csrf_cookie(request) -> str | None:
    return request.COOKIES.get(CSRF_COOKIE_NAME)


def get_csrf_header(request) -> str | None:
    value = request.META.get(CSRF_HEADER_NAME)
    return value.strip() if value else None


def csrf_is_valid(request) -> bool:
    """
    Double-submit check: the header value must be present and match
    the cookie value exactly. An attacker can make a victim's browser
    SEND the cookie automatically, but can't READ it cross-origin to
    forge a matching header — that's the whole defense.
    """

    cookie_value = get_csrf_cookie(request)
    header_value = get_csrf_header(request)

    if not cookie_value or not header_value:
        return False

    return hmac.compare_digest(cookie_value, header_value)
