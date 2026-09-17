from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Literal

import jwt as pyjwt
from jwt import InvalidTokenError

from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.utils.security.jwt_keys import get_private_key, get_public_key

ALGORITHM = "RS256"
ACCESS = "access"
REFRESH = "refresh"


class TokenError(Exception):
    """Raised for any invalid, expired, malformed, or wrong-type token."""


def _now() -> datetime:
    return datetime.now(tz=dt_timezone.utc)


def _issuer() -> str:
    return getattr(auth_config, "jwt_issuer", "dj_waanverse_auth")


def encode_token(
    *,
    account_id,
    session_id,
    token_type: Literal["access", "refresh"],
    lifetime: timedelta,
) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at)."""

    jti = str(uuid.uuid4())
    now = _now()
    expires_at = now + lifetime

    payload = {
        "sub": str(account_id),
        "sid": str(session_id),
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
        "iss": _issuer(),
    }

    token = pyjwt.encode(payload, get_private_key(), algorithm=ALGORITHM)
    return token, jti, expires_at


def decode_token(token: str, *, expected_type: Literal["access", "refresh"]) -> dict:
    """
    Fully validates a JWT: signature, expiry, issuer, required claims,
    and that it's the expected type — so a refresh token can never be
    used where an access token is expected, or vice versa. Raises
    TokenError uniformly; callers never need to know pyjwt's own
    exception hierarchy.
    """

    try:
        payload = pyjwt.decode(
            token,
            get_public_key(),
            algorithms=[
                ALGORITHM
            ],  # explicit allow-list — never trust the token's own header
            issuer=_issuer(),
            options={"require": ["exp", "iat", "sub", "sid", "type", "jti"]},
        )
    except InvalidTokenError as exc:
        raise TokenError(str(exc)) from exc

    if payload.get("type") != expected_type:
        raise TokenError(
            f"Expected a {expected_type} token, got {payload.get('type')}."
        )

    return payload
