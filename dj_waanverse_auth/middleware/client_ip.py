from __future__ import annotations

from ipaddress import ip_address as parse_ip
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class IPAddressMiddleware:
    """
    Best-effort resolution of the client's IP address, attached as
    request.ip_address (str | None).

    This is informational, not a security control: X-Forwarded-For
    and CF-Connecting-IP are trivially spoofable by a client unless
    verified against a trusted proxy. request.ip_address is fine for
    session/device metadata and display, but should not be treated
    as authoritative for access decisions without that verification
    being added later.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.ip_address = self._resolve(request)
        return self.get_response(request)

    def _resolve(self, request: HttpRequest) -> str | None:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            candidate = forwarded_for.split(",")[0].strip()
            if self._is_valid(candidate):
                return candidate

        cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")
        if cf_ip and self._is_valid(cf_ip):
            return cf_ip

        remote_addr = request.META.get("REMOTE_ADDR")
        if remote_addr and self._is_valid(remote_addr):
            return remote_addr

        return None

    @staticmethod
    def _is_valid(value: str) -> bool:
        try:
            parse_ip(value.strip())
            return True
        except ValueError:
            return False
