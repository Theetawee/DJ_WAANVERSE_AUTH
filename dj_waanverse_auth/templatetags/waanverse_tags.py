import requests
from django import template
from django.core.cache import cache
from user_agents import parse

register = template.Library()


@register.filter
def device_info(user_agent):
    try:
        user_agent_parsed = parse(user_agent)

        browser = user_agent_parsed.browser.family or "Unknown"
        device = user_agent_parsed.device.family or "Unknown"
        os = user_agent_parsed.os.family or "Unknown"

        if user_agent_parsed.is_mobile:
            device_type = "Mobile"
        elif user_agent_parsed.is_tablet:
            device_type = "Tablet"
        elif user_agent_parsed.is_pc:
            device_type = "PC"
        else:
            device_type = "Unknown"

        return f"Browser: {browser}, Device: {device}, OS: {os}, Type: {device_type}"
    except Exception:
        # If parsing fails, assume it's a mobile app or unknown user agent
        return "Device: Mobile App or Unknown Device"


@register.filter
def country(ip):
    # Check if the country is already cached
    cached_country = cache.get(f"ip_country_{ip}")
    if cached_country:
        return cached_country

    # Fetch location data from IP API
    url = f"http://ip-api.com/json/{ip}"
    response = requests.get(url)
    data = response.json()
    country = data.get("country", f"{ip}")

    # Cache the result for 1 hour (3600 seconds)
    cache.set(f"ip_country_{ip}", country, timeout=3600)

    return country
