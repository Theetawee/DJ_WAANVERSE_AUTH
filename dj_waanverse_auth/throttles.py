# dj_waanverse_auth/throttles.py
from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured
from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class BaseIPThrottle(SimpleRateThrottle):
    """
    Generic per-IP throttle. Subclasses set `scope` to a key matching
    DEFAULT_THROTTLE_RATES. Depends on IPAddressMiddleware having set
    request.ip_address — NOT request.client_ip, which no longer
    exists since ClientIPMiddleware was removed.
    """

    scope: str

    def get_cache_key(self, request, view):
        client_ip = getattr(request, "ip_address", None)

        if client_ip is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} requires IPAddressMiddleware to be "
                "installed and to run before this throttle."
            )

        return self.cache_format % {"scope": self.scope, "ident": client_ip}


class BaseIdentifierThrottle(SimpleRateThrottle):
    """
    Generic per-identifier throttle, keyed off request.data["identifier"],
    normalized (stripped + lowercased) so case/whitespace variants of
    the same identifier share one bucket. Returns None (DRF's "skip
    this throttle" signal) when no identifier was submitted — that's
    the view's own validation's job to reject, not this throttle's.
    """

    scope: str
    IDENTIFIER_FIELD = "identifier"

    def get_cache_key(self, request, view):
        identifier = self.get_identifier(request)
        if not identifier:
            return None
        return self.cache_format % {"scope": self.scope, "ident": identifier}

    def get_identifier(self, request) -> str | None:
        value = request.data.get(self.IDENTIFIER_FIELD)
        if not isinstance(value, str) or not value.strip():
            return None
        return value.strip().lower()


# ---------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------


class SignupIPThrottle(BaseIPThrottle):
    scope = "signup-ip"


class SignupIdentifierThrottle(BaseIdentifierThrottle):
    scope = "signup-identifier"


# ---------------------------------------------------------------------
# Login — the highest-value target (credential stuffing)
# ---------------------------------------------------------------------


class LoginIPThrottle(BaseIPThrottle):
    scope = "login-ip"


class LoginIdentifierThrottle(BaseIdentifierThrottle):
    scope = "login-identifier"


# ---------------------------------------------------------------------
# Verification (resend code/link) — email/SMS bombing prevention
# ---------------------------------------------------------------------


class VerificationRequestIPThrottle(BaseIPThrottle):
    scope = "verification-request-ip"


class VerificationRequestIdentifierThrottle(BaseIdentifierThrottle):
    scope = "verification-request-identifier"


class VerifyAccountIPThrottle(BaseIPThrottle):
    """
    Confirm step. MAX_ATTEMPTS already caps guesses against ONE
    issued code; this additionally slows an attacker rotating
    across many different accounts/identifiers from one IP.
    """

    scope = "verify-account-ip"


# ---------------------------------------------------------------------
# Password reset — same shape as verification, same reasoning
# ---------------------------------------------------------------------


class PasswordResetRequestIPThrottle(BaseIPThrottle):
    scope = "password-reset-request-ip"


class PasswordResetRequestIdentifierThrottle(BaseIdentifierThrottle):
    scope = "password-reset-request-identifier"


class PasswordResetConfirmIPThrottle(BaseIPThrottle):
    scope = "password-reset-confirm-ip"


# ---------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------


class RefreshIPThrottle(BaseIPThrottle):
    """
    Reuse-detection already prevents an old refresh token being
    replayed, but this stops raw volume — rapid-fire refresh calls
    hammering the cache/DB regardless of token validity.
    """

    scope = "refresh-ip"


class SessionActionsThrottle(UserRateThrottle):
    scope = "session-actions"
