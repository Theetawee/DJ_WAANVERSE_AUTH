# dj_waanverse_auth/middleware.py
from __future__ import annotations

from ipaddress import ip_address as parse_ip, ip_network
from typing import TYPE_CHECKING

from django.core.exceptions import ImproperlyConfigured

from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.utils.cloudflare_ranges import CLOUDFLARE_IP_RANGES

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

LOCALHOST_RANGES = ["127.0.0.1/32", "::1/128"]


class IPAddressMiddleware:
    """
    Best-effort resolution of the client's IP address, attached as
    request.ip_address (str | None).

    Forwarded headers are only trusted when the immediate connecting
    peer (REMOTE_ADDR) is inside a known-trusted range:

    - Cloudflare's published ranges — always trusted.
    - Localhost — trusted UNLESS trust_cloudflare_only is set. Set
      this True in production if nothing but Cloudflare should ever
      be trusted to supply forwarded headers; leave it False (the
      default outside DEBUG=False... see below) to also trust a
      single local reverse proxy (e.g. nginx on the same box).

    Default: trust_cloudflare_only follows `not DEBUG` unless
    explicitly set — i.e. production defaults to Cloudflare-only,
    dev defaults to also trusting localhost.

    Header priority when the peer IS trusted:
    - If the peer is Cloudflare: prefer CF-Connecting-IP (Cloudflare's
      own direct claim). Fall back to the LAST valid entry in
      X-Forwarded-For if CF-Connecting-IP is absent.
    - If the peer is a trusted local proxy (not Cloudflare): use the
      LAST valid entry in X-Forwarded-For — a well-behaved proxy
      APPENDS the address it saw rather than replacing the header,
      so earlier entries can be attacker-supplied; only the last one
      reflects what the trusted hop actually observed.

    A request from an untrusted peer never has either header
    consulted; request.ip_address falls back to the raw REMOTE_ADDR.

    This is purely informational, not a security control on its own
    — a request is never rejected here regardless of trust status.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.cloudflare_only = auth_config.trust_cloudflare_only
        self.cloudflare_networks = self._load_networks(CLOUDFLARE_IP_RANGES)
        self.localhost_networks = (
            () if self.cloudflare_only else self._load_networks(LOCALHOST_RANGES)
        )

        if not self.cloudflare_networks:
            raise ImproperlyConfigured(
                "IPAddressMiddleware has no valid Cloudflare IP ranges configured."
            )

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.ip_address = self._resolve(request)
        return self.get_response(request)

    def _resolve(self, request: HttpRequest) -> str | None:
        remote_addr = request.META.get("REMOTE_ADDR")
        remote_ip = self._parse(remote_addr)

        if remote_ip is not None:
            if self._in_networks(remote_ip, self.cloudflare_networks):
                cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")
                if cf_ip and self._is_valid(cf_ip):
                    return cf_ip.strip()

                forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
                if forwarded_for:
                    last = self._last_valid_ip(forwarded_for)
                    if last:
                        return last

            elif self._in_networks(remote_ip, self.localhost_networks):
                forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
                if forwarded_for:
                    last = self._last_valid_ip(forwarded_for)
                    if last:
                        return last

        if remote_addr and self._is_valid(remote_addr):
            return remote_addr.strip()

        return None

    @staticmethod
    def _in_networks(address, networks) -> bool:
        return any(address in network for network in networks)

    @staticmethod
    def _load_networks(cidrs):
        networks = []
        for cidr in cidrs:
            try:
                networks.append(ip_network(cidr, strict=False))
            except ValueError:
                continue
        return tuple(networks)

    @staticmethod
    def _parse(value):
        if not value:
            return None
        try:
            return parse_ip(value.strip())
        except ValueError:
            return None

    @staticmethod
    def _is_valid(value: str) -> bool:
        try:
            parse_ip(value.strip())
            return True
        except ValueError:
            return False

    @staticmethod
    def _last_valid_ip(header_value: str):
        """
        Scans from the end of a comma-separated header for the last
        entry that actually parses as an IP, skipping trailing junk
        rather than failing outright on one malformed entry.
        """
        parts = [p.strip() for p in header_value.split(",") if p.strip()]
        for candidate in reversed(parts):
            if IPAddressMiddleware._is_valid(candidate):
                return candidate
        return None
