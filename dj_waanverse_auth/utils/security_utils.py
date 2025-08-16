import logging
from ipaddress import ip_address, ip_network
from typing import Optional

import requests
from user_agents import parse


from .constants import TRUSTED_PROXIES

logger = logging.getLogger(__name__)


def is_cloudflare_ip(ip: str) -> bool:
    """
    Verify if an IP belongs to Cloudflare's network.

    Args:
        ip (str): IP address to check

    Returns:
        bool: True if IP is from Cloudflare's network, False otherwise
    """
    try:
        ip_obj = ip_address(ip)
        return any(ip_obj in ip_network(cf_range) for cf_range in TRUSTED_PROXIES)
    except ValueError:
        return False


def get_ip_address(request) -> Optional[str]:
    """
    Extracts the real IP address from the request with Cloudflare verification.

    Args:
        request: The HTTP request object

    Returns:
        Optional[str]: The client IP address if it can be reliably determined
    """
    # First check if request is from Cloudflare
    remote_addr = request.META.get("REMOTE_ADDR")
    cf_connecting_ip = request.META.get("HTTP_CF_CONNECTING_IP")

    if remote_addr and cf_connecting_ip:
        if is_cloudflare_ip(remote_addr):
            return cf_connecting_ip

    # If not from Cloudflare, try X-Forwarded-For
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        # Get the first IP in the chain
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    # Fall back to REMOTE_ADDR if everything else fails
    return remote_addr if remote_addr else None


def get_location_from_ip(ip_address: str) -> str:
    """Gets location details from an IP address and returns a formatted location string."""
    if ip_address == "127.0.0.1":
        return "Unknown"
    try:
        response = requests.get(f"https://ipinfo.io/{ip_address}")
        response.raise_for_status()
        data = response.json()

        if not data:
            return "Unknown"

        # Get location fields, default to 'Unknown' if not found
        country = data.get("country", "Unknown")
        city = data.get("city", "Unknown")
        region = data.get("region", "Unknown")

        # Construct the location string, skipping "Unknown" parts
        location_parts = [
            part for part in [city, region, country] if part and part != "Unknown"
        ]

        if not location_parts:
            return "Unknown"  # All parts are "Unknown"

        return ", ".join(location_parts)  # Join non-Unknown parts into a string

    except requests.RequestException as e:
        logger.error(f"Error fetching IP location: {e}")
        return "Unknown"


def get_device(request):
    """Extracts device information from the request using user_agents."""
    user_agent = request.META.get("HTTP_USER_AGENT", "").strip()

    if not user_agent:
        return "Unknown device"

    # Parse the user agent string
    ua = parse(user_agent)

    # Extract device details
    device_info = []

    # Only add non-unknown details
    if ua.device.family != "Other":
        device_info.append(ua.device.family)
    if ua.os.family != "Unknown":
        device_info.append(ua.os.family)
    if ua.browser.family != "Unknown":
        device_info.append(ua.browser.family)

    # Return a formatted string or "Unknown device" if no info
    if not device_info:
        return "Unknown device"

    return " on ".join(device_info)
