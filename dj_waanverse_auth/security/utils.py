import logging
from ipaddress import ip_address, ip_network
from typing import Dict

import requests
from user_agents import parse  # pip install pyyaml ua-parser user-agents

logger = logging.getLogger(__name__)


# last update : Sep 28, 2023:
TRUSTED_PROXIES = [
    # # IPv4 ranges
    # "127.0.0.1",  # localhost
    # "192.168.0.0/16",  # local networks
    "173.245.48.0/20",
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "131.0.72.0/22",
    # IPv6 ranges
    "2400:cb00::/32",
    "2606:4700::/32",
    "2803:f800::/32",
    "2405:b500::/32",
    "2405:8100::/32",
    "2a06:98c0::/29",
    "2c0f:f248::/32",
]


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


def parse_user_agent(user_agent_string: str) -> Dict[str, str]:
    """
    Parse User-Agent string to extract detailed device information
    """
    if not user_agent_string:
        return {
            "device_type": "unknown",
            "browser": "unknown",
            "os": "unknown",
            "device_name": "unknown",
        }

    # Parse using user-agents library
    user_agent = parse(user_agent_string)

    # Determine device type more accurately
    if user_agent.is_mobile:
        device_type = "mobile"
    elif user_agent.is_tablet:
        device_type = "tablet"
    elif user_agent.is_pc:
        device_type = "desktop"
    else:
        device_type = "other"

    return {
        "device_type": device_type,
        "browser": f"{user_agent.browser.family} {user_agent.browser.version_string}",
        "os": f"{user_agent.os.family} {user_agent.os.version_string}",
        "device_name": user_agent.device.family,
        "is_bot": user_agent.is_bot,
        "browser_family": user_agent.browser.family,
        "os_family": user_agent.os.family,
    }
