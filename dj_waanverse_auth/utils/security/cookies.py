# dj_waanverse_auth/utils/cookies.py
from __future__ import annotations
from dj_waanverse_auth.utils.security.csrf import CSRF_COOKIE_NAME, generate_csrf_token

from typing import TYPE_CHECKING

from django.utils import timezone

from dj_waanverse_auth import settings as auth_config

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.response import Response
    from dj_waanverse_auth.utils.security.tokens import IssuedTokens

MOBILE_CLIENT_HEADER = (
    "HTTP_X_CLIENT_TYPE"  # client sends header "X-Client-Type: mobile"
)


def _cookie_settings() -> dict:
    return {
        "access_name": auth_config.access_token_cookie_name,
        "refresh_name": auth_config.refresh_token_cookie_name,
        "domain": auth_config.cookie_domain,
        "secure": auth_config.cookie_secure,
        "samesite": auth_config.cookie_samesite,
        "path": auth_config.cookie_path,
    }


def is_mobile_client(request: "Request") -> bool:
    return request.META.get(MOBILE_CLIENT_HEADER, "").lower() == "mobile"


def set_auth_cookies(response, tokens):
    settings_ = _cookie_settings()
    now = timezone.now()

    response.set_cookie(
        settings_["access_name"],
        tokens.access_token,
        max_age=int((tokens.access_expires_at - now).total_seconds()),
        httponly=True,
        secure=settings_["secure"],
        samesite=settings_["samesite"],
        domain=settings_["domain"],
        path=settings_["path"],
    )
    response.set_cookie(
        settings_["refresh_name"],
        tokens.refresh_token,
        max_age=int((tokens.refresh_expires_at - now).total_seconds()),
        httponly=True,
        secure=settings_["secure"],
        samesite=settings_["samesite"],
        domain=settings_["domain"],
        path=settings_["path"],
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        generate_csrf_token(),
        max_age=int(
            (tokens.refresh_expires_at - now).total_seconds()
        ),  # lives as long as the session can
        httponly=False,  # deliberately readable by JS — that's the whole mechanism
        secure=settings_["secure"],
        samesite=settings_["samesite"],
        domain=settings_["domain"],
        path=settings_["path"],
    )

    return response


def clear_auth_cookies(response: "Response") -> "Response":
    """Used on logout to remove both auth cookies."""

    settings_ = _cookie_settings()
    response.delete_cookie(
        settings_["access_name"], domain=settings_["domain"], path=settings_["path"]
    )
    response.delete_cookie(
        settings_["refresh_name"], domain=settings_["domain"], path=settings_["path"]
    )
    response.delete_cookie(
        CSRF_COOKIE_NAME, domain=settings_["domain"], path=settings_["path"]
    )
    return response


def build_auth_response(
    request: "Request", tokens: "IssuedTokens", data: dict, status_code: int
):
    """
    The single place every token-issuing view (verify, login, refresh)
    should build its response through, so the web/mobile split is
    enforced consistently rather than each view deciding separately:

    - Cookies are always set (mobile clients simply ignore them).
    - Raw tokens are included in the JSON body ONLY for clients that
      explicitly identify as mobile via X-Client-Type. A web client
      never receives the tokens in a form its own JS can read —
      that's the entire point of httponly cookies.
    """

    from rest_framework.response import (
        Response,
    )  # local import: keep DRF out of module-load path

    body = dict(data)
    if is_mobile_client(request):
        now = timezone.now()
        body.update(
            {
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token,
                "access_token_expires_in": int(
                    (tokens.access_expires_at - now).total_seconds()
                ),
                "refresh_token_expires_in": int(
                    (tokens.refresh_expires_at - now).total_seconds()
                ),
            }
        )

    response = Response(body, status=status_code)
    return set_auth_cookies(response, tokens)
