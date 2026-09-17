from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.models import Session
from dj_waanverse_auth.utils.security.jwt import (
    ACCESS,
    REFRESH,
    encode_token,
    decode_token,
    TokenError,
)


@dataclass
class IssuedTokens:
    access_token: str
    refresh_token: str
    access_expires_at: object
    refresh_expires_at: object
    session_id: str


def _access_lifetime() -> timedelta:
    return auth_config.access_token_lifetime


def _refresh_lifetime() -> timedelta:
    return auth_config.refresh_token_lifetime


def issue_tokens_for_account(account, request=None) -> IssuedTokens:
    """
    Creates a new session and issues a fresh access/refresh pair for
    it. Called at login, and at successful verification (auto-login).
    """

    session = Session.objects.create(
        account=account,
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""),
        ip_address=(getattr(request, "ip_address", None) if request else None),
    )

    access_token, _, access_expires_at = encode_token(
        account_id=account.pk,
        session_id=session.id,
        token_type=ACCESS,
        lifetime=_access_lifetime(),
    )
    refresh_token, _, refresh_expires_at = encode_token(
        account_id=account.pk,
        session_id=session.id,
        token_type=REFRESH,
        lifetime=_refresh_lifetime(),
    )

    session.set_refresh_token(refresh_token)
    session.save(update_fields=["refresh_token_hash"])

    return IssuedTokens(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
        session_id=str(session.id),
    )


class RefreshError(Exception):
    """Invalid, expired, revoked, or reused refresh token."""


def rotate_refresh_token(raw_refresh_token: str) -> IssuedTokens:
    """
    Verifies a refresh token, then rotates it: issues a new
    access/refresh pair for the same session, invalidating the
    supplied token.

    If the token's signature and claims are valid but it no longer
    matches the session's *currently stored* hash, that means this
    exact token was already used once before to rotate — i.e.
    someone is replaying an old refresh token (stolen and used after
    the legitimate client already rotated past it). Treated as
    compromise: the whole session is revoked, not just this request
    rejected, since a legitimate client would never present a
    superseded token.
    """

    try:
        payload = decode_token(raw_refresh_token, expected_type=REFRESH)
    except TokenError as exc:
        raise RefreshError(str(exc)) from exc

    try:
        session = Session.objects.get(pk=payload["sid"], account_id=payload["sub"])
    except Session.DoesNotExist:
        raise RefreshError("Session not found.")

    if session.is_revoked:
        raise RefreshError("Session has been revoked.")

    if not session.refresh_token_matches(raw_refresh_token):
        session.revoke()
        raise RefreshError("Refresh token reuse detected; session revoked.")

    new_access_token, _, new_access_expires_at = encode_token(
        account_id=session.account_id,
        session_id=session.id,
        token_type=ACCESS,
        lifetime=_access_lifetime(),
    )
    new_refresh_token, _, new_refresh_expires_at = encode_token(
        account_id=session.account_id,
        session_id=session.id,
        token_type=REFRESH,
        lifetime=_refresh_lifetime(),
    )

    session.set_refresh_token(new_refresh_token)
    session.last_used_at = timezone.now()
    session.save(update_fields=["refresh_token_hash", "last_used_at"])

    return IssuedTokens(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        access_expires_at=new_access_expires_at,
        refresh_expires_at=new_refresh_expires_at,
        session_id=str(session.id),
    )
