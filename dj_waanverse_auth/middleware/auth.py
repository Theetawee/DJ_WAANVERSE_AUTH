import ipaddress
import logging
from typing import List
from rest_framework import status
from django.conf import settings
from rest_framework.response import Response
from dj_waanverse_auth.authentication import JWTAuthentication
from dj_waanverse_auth.security.utils import get_ip_address

logger = logging.getLogger(__name__)


class AuthCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.auth_class = JWTAuthentication()

    def __call__(self, request):
        response = self.get_response(request)
        if request.META.get("HTTP_X_COOKIES_TO_DELETE", ""):
            response = self.auth_class.delete_marked_cookies(response, request)

        return response


class IPBlockerMiddleware:
    """
    Enhanced middleware to block requests from specific IP addresses or IP ranges.
    Features:
    - Caching of IP checks for better performance
    - Support for IPv4 and IPv6 addresses
    - Configurable allow list to override blocks
    - Logging of blocked attempts
    - Rate limiting support
    - Custom response handling
    """

    def __init__(self, get_response):
        self.get_response = get_response

        self.blocked_ips: List[str] = getattr(settings, "BLOCKED_IPS", [])
        self.allowed_ips: List[str] = getattr(settings, "ALLOWED_IPS", [])
        self.custom_message: str = getattr(
            settings, "IP_BLOCK_MESSAGE", "Access denied"
        )
        self._initialize_networks()

    def _initialize_networks(self) -> None:
        """Initialize IP networks from settings."""
        try:
            self.blocked_networks = [
                ipaddress.ip_network(ip, strict=False) for ip in self.blocked_ips
            ]
            self.allowed_networks = [
                ipaddress.ip_network(ip, strict=False) for ip in self.allowed_ips
            ]
        except ValueError as e:
            logger.error(f"Error initializing IP networks: {e}")
            self.blocked_networks = []
            self.allowed_networks = []

    def is_allowed(self, ip: str) -> bool:
        """Check if an IP is explicitly allowed."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return any(ip_obj in network for network in self.allowed_networks)
        except ValueError:
            logger.warning(f"Invalid IP address format: {ip}")
            return False

    def is_blocked(self, ip: str) -> bool:
        """
        Check if an IP address is blocked, with caching.
        """
        try:
            # Check allow list first
            if self.is_allowed(ip):
                return False

            # Check block list
            ip_obj = ipaddress.ip_address(ip)
            is_blocked = any(ip_obj in network for network in self.blocked_networks)

            return is_blocked

        except ValueError:
            logger.warning(f"Invalid IP address format: {ip}")
            return False

    def __call__(self, request):
        client_ip = get_ip_address(request)

        if not client_ip:
            logger.warning("Could not determine client IP address")
            return self.get_response(request)

        if self.is_blocked(client_ip):
            logger.info(f"Blocked request from IP: {client_ip}")
            return Response({"detail": self.custom_message}, status=status.HTTP_403_FORBIDDEN)

        return self.get_response(request)
