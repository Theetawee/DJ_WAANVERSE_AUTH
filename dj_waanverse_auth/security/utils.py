import logging
from ipaddress import ip_address, ip_network

import requests
from django.utils.translation import gettext_lazy as _
from user_agents import parse

from dj_waanverse_auth.config.settings import auth_config

from .constants import TRUSTED_PROXIES

logger = logging.getLogger(__name__)


def get_ip_address(request):
    """Extracts the real IP address from the request."""

    def is_trusted_proxy(ip):
        return any(ip_address(ip) in ip_network(proxy) for proxy in TRUSTED_PROXIES)

    ip_headers = [
        ("HTTP_CF_CONNECTING_IP", None),
        ("HTTP_X_FORWARDED_FOR", lambda x: x.split(",")[0].strip()),
        ("HTTP_X_REAL_IP", None),
        ("REMOTE_ADDR", None),
    ]

    for header, processor in ip_headers:
        ip = request.META.get(header)
        if ip:
            if processor:
                ip = processor(ip)
            if not is_trusted_proxy(ip):
                return ip

    return None


def get_location_from_ip(ip_address: str) -> str:
    """Gets location details from an IP address and returns a formatted location string."""
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


TURNSTILE_API_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def validate_turnstile_token(token):
    """
    Validate the Turnstile captcha token with the external service.

    Args:
        token (str): The Turnstile token received from the client.

    Returns:
        bool: True if the token is valid, False otherwise.
    """
    # Get your Turnstile secret key from the settings
    secret_key = auth_config.cloudflare_turnstile_secret

    if not secret_key:
        raise ValueError(_("Turnstile secret key is not configured."))

    response = requests.post(
        TURNSTILE_API_URL, data={"secret": secret_key, "response": token}
    )

    if response.status_code != 200:
        raise Exception(_("Error while validating Turnstile token."))

    result = response.json()

    if result.get("success"):
        return True

    return False
