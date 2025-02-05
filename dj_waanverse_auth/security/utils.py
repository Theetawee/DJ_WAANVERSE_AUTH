import logging
from ipaddress import ip_address, ip_network
from typing import Optional

import requests
import six
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import signing
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from user_agents import parse

from dj_waanverse_auth import settings

from .constants import TRUSTED_PROXIES
from .validators import ValidateData

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
    secret_key = settings.cloudflare_turnstile_secret

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


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Generate unique tokens for email verification that expire and are single-use
    by incorporating timestamp and verification status in the hash.
    """

    def _make_hash_value(self, user, timestamp):
        """
        Create a unique hash incorporating user state and email verification status.
        This ensures the token becomes invalid once used (since email_verified changes).
        """
        login_timestamp = (
            ""
            if not user.last_login
            else user.last_login.replace(microsecond=0, tzinfo=None)
        )
        return (
            # User state that invalidates the token if changed
            six.text_type(user.pk)
            + six.text_type(user.email_verified)
            + six.text_type(login_timestamp)
            +
            # Timestamp for expiration
            six.text_type(timestamp)
        )

    def check_token(
        self,
        user,
        token,
        max_age_minutes=settings.verification_email_code_expiry_in_minutes,
    ):
        """
        Check if the token is valid and not expired.

        Args:
            user: The user object
            token: The token to verify
            max_age_minutes: Maximum age of token in minutes
        """
        try:
            timestamp_b36 = token.split("-")[0]
            ts = int(timestamp_b36, 36)
            now = self._now()
            if (now - ts) > (max_age_minutes * 60):
                return False
            return super().check_token(user, token)
        except Exception:
            return False


def generate_verify_email_url(
    user,
    email_address,
    expiry_minutes=settings.verification_email_code_expiry_in_minutes,
):
    """
    Generate a unique URL for email verification that expires and is single-use.

    Args:
        user (Account): The user object
        expiry_minutes (int): Number of minutes until URL expires

    Returns:
        str: The verification URL
    """
    validator = ValidateData()
    cleaned_data = validator.validate_email(email_address, check_uniqueness=True)
    print(cleaned_data)
    if cleaned_data.get("is_valid") is False:
        raise ValueError(cleaned_data.get("errors")[0])
    else:
        email_address = cleaned_data.get("value")
    # Generate token using our custom generator
    generator = EmailVerificationTokenGenerator()
    token = generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # Create a signed payload that includes necessary verification data
    payload = {
        "uid": uid,
        "token": token,
        "email": email_address,
        "exp": timezone.now().timestamp() + (expiry_minutes * 60),
    }

    signed_value = signing.dumps(payload, salt="email-verification", compress=True)

    verification_url = f"{settings.verify_email_url}?token={signed_value}"

    return verification_url


def verify_email_token(signed_token, user):
    """
    Verify the email verification token.

    Args:
        signed_token (str): The signed token from the URL
        user (Account): The user object

    Returns:
        bool: True if token is valid, False otherwise
    """
    try:
        # First verify and decode the signed payload
        payload = signing.loads(
            signed_token,
            salt="email-verification",
            max_age=1800,
        )

        # Check if token has expired
        if payload["exp"] < timezone.now().timestamp():
            return False

        if payload["email"] != user.email:
            return False

        # Verify the actual token
        generator = EmailVerificationTokenGenerator()
        is_valid = generator.check_token(
            user,
            payload["token"],
            max_age_minutes=settings.verification_email_code_expiry_in_minutes,
        )

        return is_valid

    except (signing.BadSignature, signing.SignatureExpired, KeyError):
        return False
