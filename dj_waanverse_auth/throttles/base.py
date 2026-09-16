# dj_waanverse_auth/throttling.py
from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ImproperlyConfigured
from rest_framework.throttling import SimpleRateThrottle

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


class SignupIPThrottle(SimpleRateThrottle):
    """
    Limit signup attempts per client IP address, regardless of the
    identifier (email/username) submitted.

    Depends on ``ClientIPMiddleware`` having set ``request.client_ip``.
    Configure the rate via DRF's standard throttle rate setting:

        REST_FRAMEWORK = {
            "DEFAULT_THROTTLE_RATES": {
                "signup-ip": "10/hour",
            },
        }
    """

    scope = "signup-ip"

    def get_cache_key(self, request: Request, view: APIView):
        client_ip = getattr(request, "client_ip", None)

        if client_ip is None:
            raise ImproperlyConfigured(
                "SignupIPThrottle requires ClientIPMiddleware to be "
                "installed and to run before this throttle."
            )

        return self.cache_format % {
            "scope": self.scope,
            "ident": client_ip,
        }


class SignupIdentifierThrottle(SimpleRateThrottle):
    """
    Limit signup attempts per submitted identifier, regardless of
    client IP.

    Configure the rate via DRF's standard throttle rate setting:

        REST_FRAMEWORK = {
            "DEFAULT_THROTTLE_RATES": {
                "signup-identifier": "5/hour",
            },
        }
    """

    scope = "signup-identifier"

    IDENTIFIER_FIELD = "identifier"

    def get_cache_key(self, request: Request, view: APIView):
        identifier = self.get_identifier(request)

        if not identifier:
            # No identifier submitted yet — let the view's own
            # validation reject the request instead of throttling it.
            return None

        return self.cache_format % {
            "scope": self.scope,
            "ident": identifier,
        }

    def get_identifier(self, request: Request) -> str | None:
        """
        Extract and normalize the identifier used to key this throttle.

        Override this (or set ``IDENTIFIER_FIELD``) if signup uses a
        different field name.
        """

        value = request.data.get(self.IDENTIFIER_FIELD)

        if not isinstance(value, str) or not value.strip():
            return None

        return value.strip().lower()
