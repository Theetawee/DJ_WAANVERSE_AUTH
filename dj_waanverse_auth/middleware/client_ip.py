from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address
from ipaddress import ip_address, ip_network
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseForbidden

from dj_waanverse_auth.utils.cloudflare_ranges import CLOUDFLARE_IP_RANGES

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class ClientIPMiddleware:
    """
    Resolve the real client IP from Cloudflare.

    This middleware assumes that the Django application is only
    accessible through Cloudflare.

    A request is considered trusted only when:

        REMOTE_ADDR
            belongs to a configured Cloudflare network

    and:

        CF-Connecting-IP
            contains a valid IP address.

    Any request that fails verification is rejected with a 403.

    The resolved address is exposed as:

        request.client_ip
        request.client_ip_source

    Example:

        request.client_ip
        # "197.123.45.67"

        request.client_ip_source
        # "cloudflare"

    In development (settings.DEBUG = True), Cloudflare verification
    is skipped entirely and REMOTE_ADDR is trusted directly.

        request.client_ip_source
        # "debug"
    """

    CF_CONNECTING_IP_HEADER = "HTTP_CF_CONNECTING_IP"

    SOURCE_CLOUDFLARE = "cloudflare"
    SOURCE_DEBUG = "debug"

    def __init__(self, get_response):
        self.get_response = get_response

        self.debug = getattr(settings, "DEBUG", False)

        self.cloudflare_networks = self._load_cloudflare_networks()

        if not self.debug and not self.cloudflare_networks:
            raise ImproperlyConfigured(
                "Waanverse Auth requires at least one Cloudflare "
                "IP range to be configured."
            )

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self.debug:
            debug_ip = self._parse_ip(request.META.get("REMOTE_ADDR"))

            if debug_ip is None:
                return HttpResponseForbidden("Unable to verify client IP.")

            request.client_ip = str(debug_ip)
            request.client_ip_source = self.SOURCE_DEBUG

            return self.get_response(request)

        client_ip = self.resolve_client_ip(request)

        if client_ip is None:
            return HttpResponseForbidden("Unable to verify client IP.")

        request.client_ip = str(client_ip)
        request.client_ip_source = self.SOURCE_CLOUDFLARE

        return self.get_response(request)

    def resolve_client_ip(self, request: HttpRequest):
        """
        Resolve and return the verified client IP.

        Returns:
            IPv4Address | IPv6Address | None
        """

        remote_addr = request.META.get("REMOTE_ADDR")

        if not self._is_cloudflare_ip(remote_addr):
            return None

        forwarded_ip = request.META.get(self.CF_CONNECTING_IP_HEADER)

        return self._parse_ip(forwarded_ip)

    def _is_cloudflare_ip(self, value: str | None) -> bool:
        """
        Check whether the immediate peer is inside
        one of Cloudflare's trusted networks.
        """

        address = self._parse_ip(value)

        if address is None:
            return False

        return any(address in network for network in self.cloudflare_networks)

    @staticmethod
    def _parse_ip(
        value: str | None,
    ) -> IPv4Address | IPv6Address | None:
        """
        Parse an IPv4 or IPv6 address safely.
        """

        if not value:
            return None

        try:
            address = ip_address(value.strip())
        except ValueError:
            return None

        return address

    def _load_cloudflare_networks(self):
        """
        Convert configured CIDR strings into ip_network objects.
        """

        networks = []

        for cidr in CLOUDFLARE_IP_RANGES:
            try:
                networks.append(ip_network(cidr, strict=False))
            except ValueError as exc:
                raise ImproperlyConfigured(
                    f"Invalid Cloudflare IP range: {cidr}"
                ) from exc

        return tuple(networks)
