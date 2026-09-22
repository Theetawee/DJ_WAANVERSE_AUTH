# dj_waanverse_auth/views/logout_views.py
from __future__ import annotations

from logging import getLogger

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from dj_waanverse_auth.authentication import (
    enforce_csrf_if_cookie_sourced,
    get_refresh_token,
)
from dj_waanverse_auth.models import Session
from dj_waanverse_auth.utils.security.cookies import clear_auth_cookies
from dj_waanverse_auth.utils.security.jwt import REFRESH, TokenError, decode_token

logger = getLogger(__name__)


class LogoutView(APIView):
    """
    Revokes the session behind the presented refresh token and
    clears auth cookies. Deliberately AllowAny, and deliberately NOT
    using JWTAuthentication (which only ever reads ACCESS tokens) —
    logout must keep working even when the access token has already
    expired, since "my access token is stale" is one of the most
    common reasons someone hits logout at all.

    The refresh token is what proves ownership (its hash must match
    Session.refresh_token_hash) — not a bare session id. A session id
    alone isn't a secret: it's readable inside any access or refresh
    JWT's payload without even checking the signature. Accepting a
    raw sid to revoke-by-ID would let anyone who ever saw that id
    (a stolen token, a log line, a leaked value) revoke that session
    at will, indefinitely, with no further proof required.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh_token, source = get_refresh_token(request)

        if raw_refresh_token:
            enforce_csrf_if_cookie_sourced(request, source)
            self._revoke_if_valid(raw_refresh_token)

        response = Response({"msg": "Logged out."}, status=status.HTTP_200_OK)
        return clear_auth_cookies(response)

    def _revoke_if_valid(self, raw_refresh_token: str) -> None:
        """
        Best-effort: revoke the matching session if the token is
        valid and actually matches. Any failure (expired, malformed,
        session missing, already superseded) is swallowed here —
        logout always reports success and always clears cookies
        regardless, because the caller's intent is "get me logged
        out," not "prove this specific token was still valid."
        """
        try:
            payload = decode_token(raw_refresh_token, expected_type=REFRESH)
        except TokenError:
            return

        try:
            session = Session.objects.get(pk=payload["sid"], account_id=payload["sub"])
        except Session.DoesNotExist:
            return

        if not session.is_revoked and session.refresh_token_matches(raw_refresh_token):
            session.revoke()
