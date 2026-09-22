from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.utils.security.csrf import csrf_is_valid
from dj_waanverse_auth.utils.security.jwt import ACCESS, TokenError, decode_token

Account = get_user_model()

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def extract_bearer_token(request) -> str | None:
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header.startswith("Bearer "):
        return None
    token = header[len("Bearer ") :].strip()  # noqa
    return token or None


def get_access_token(request) -> tuple[str | None, str | None]:
    """
    Returns (token, source) where source is "cookie" or "bearer".
    The source matters: a cookie is auto-attached by the browser on
    cross-site requests (CSRF-relevant); a Bearer header is not
    (a cross-site attacker's page can't make the victim's browser
    attach an arbitrary header) — so only cookie-sourced tokens need
    the CSRF check.
    """

    cookie_name = auth_config.access_token_cookie_name
    cookie_value = request.COOKIES.get(cookie_name)
    if cookie_value:
        return cookie_value, "cookie"

    bearer_value = extract_bearer_token(request)
    if bearer_value:
        return bearer_value, "bearer"

    return None, None


def get_refresh_token(request) -> tuple[str | None, str | None]:
    """Same cookie-then-bearer, source-tagged pattern, for refresh."""

    cookie_name = auth_config.refresh_token_cookie_name
    cookie_value = request.COOKIES.get(cookie_name)
    if cookie_value:
        return cookie_value, "cookie"

    bearer_value = extract_bearer_token(request)
    if bearer_value:
        return bearer_value, "bearer"

    return None, None


def enforce_csrf_if_cookie_sourced(request, source: str) -> None:
    """
    Call this from any view performing a state change using a
    cookie-sourced token. Raises PermissionDenied (403) if the
    double-submit CSRF header is missing or doesn't match the
    cookie. No-op for bearer-sourced tokens or safe HTTP methods.
    """

    if source != "cookie":
        return
    if request.method in SAFE_METHODS:
        return
    if not csrf_is_valid(request):
        raise PermissionDenied("CSRF token missing or invalid.")


class JWTAuthentication(BaseAuthentication):
    """
    Authenticates via an access token, cookie first then Bearer
    header. For cookie-sourced tokens on unsafe methods, also
    enforces the double-submit CSRF check — see
    enforce_csrf_if_cookie_sourced for why bearer tokens are exempt.
    """

    def authenticate(self, request):
        token, source = get_access_token(request)
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

        enforce_csrf_if_cookie_sourced(request, source)

        return (account, payload)

    def authenticate_header(self, request):
        return "Bearer"

    @staticmethod
    def _get_account(payload):
        try:
            return Account.objects.get(pk=payload["sub"])
        except (Account.DoesNotExist, ValueError, TypeError):
            return None
