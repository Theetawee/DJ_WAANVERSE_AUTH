# dj_waanverse_auth/authentication.py
from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.utils.security.jwt import ACCESS, TokenError, decode_token

Account = get_user_model()


def extract_bearer_token(request) -> str | None:
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header.startswith("Bearer "):
        return None
    token = header[len("Bearer ") :].strip()  # noqa
    return token or None


def get_access_token(request) -> str | None:
    """
    Cookie first, then Authorization: Bearer header — so a web
    client (httponly cookie, no header) and a mobile/API client (no
    cookie jar, sends the header) both authenticate through the
    same lookup, without either needing to know about the other.
    """
    cookie_name = auth_config.access_token_cookie_name
    token = request.COOKIES.get(cookie_name)
    return token or extract_bearer_token(request)


def get_refresh_token(request) -> str | None:
    """Same cookie-then-header pattern, for the refresh endpoint."""
    cookie_name = auth_config.refresh_token_cookie_name
    token = request.COOKIES.get(cookie_name)
    return token or extract_bearer_token(request)


class JWTAuthentication(BaseAuthentication):
    """
    Authenticates a request using a short-lived access token, read
    from a cookie first and falling back to an Authorization: Bearer
    header if no cookie is present.

    Returns None (does not raise) when no token was supplied at
    all — DRF's convention for "this scheme wasn't attempted",
    leaving it to permission classes to decide what happens next
    (e.g. AllowAny views stay accessible). Raises AuthenticationFailed
    for any token that WAS supplied but is invalid, expired, the
    wrong type, or points at a missing/inactive account — a bad
    token must never be silently treated the same as no token.
    """

    def authenticate(self, request):
        token = get_access_token(request)
        if not token:
            return None

        try:
            payload = decode_token(token, expected_type=ACCESS)
        except TokenError as exc:
            raise AuthenticationFailed(str(exc)) from exc

        account = self._get_account(payload)
        if account is None:
            raise AuthenticationFailed("Account not found.")

        if not account.is_active:
            raise AuthenticationFailed("Account is inactive.")

        return (account, payload)

    def authenticate_header(self, request):
        # Sent back via WWW-Authenticate on a 401 — standard DRF convention.
        return "Bearer"

    @staticmethod
    def _get_account(payload):
        try:
            return Account.objects.get(pk=payload["sub"])
        except (Account.DoesNotExist, ValueError, TypeError):
            return None
