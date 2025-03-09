from typing import Dict, Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email

from dj_waanverse_auth import settings

User = get_user_model()


def _check_basic_format(email_address: str, result: dict) -> Optional[dict]:
    """Check basic email format requirements"""
    if not email_address:
        return _invalid_result(result, "Email address is required.")

    try:
        django_validate_email(email_address)
    except ValidationError:
        return _invalid_result(result, "Invalid email format.")

    if len(email_address) > 250:
        return _invalid_result(
            result, "Email address is too long (maximum 250 characters)."
        )
    return None


def _check_domain(email_address: str, result: dict) -> Optional[dict]:
    """Check domain-related validations"""
    try:
        _, domain = email_address.split("@", 1)
    except ValueError:
        return _invalid_result(result, "Invalid email format.")

    if domain in settings.disposable_email_domains:
        return _invalid_result(result, "Disposable email addresses are not allowed.")
    return None


def _check_blacklist_and_uniqueness(
    email_address: str, check_uniqueness: bool, result: dict
) -> Optional[dict]:
    """Check blacklist and uniqueness validations"""
    if email_address.lower() in settings.blacklisted_emails:
        return _invalid_result(result, "This email address is not allowed.")

    if check_uniqueness and User.objects.filter(email__iexact=email_address).exists():
        return _invalid_result(result, "Email address is already in use.")
    return None


def validate_email(
    email_address: str, check_uniqueness: bool = False
) -> Dict[str, Optional[str]]:
    """
    Validates an email address using Django's built-in validator and additional custom checks.

    Args:
        email_address: The email address to validate
        check_uniqueness: Whether to check if the email is already in use

    Returns:
        Dict containing:
            - email: The original email address
            - error: Error message if validation failed, None otherwise
            - is_valid: Boolean indicating if the email is valid
    """
    result = {"email": email_address, "error": None, "is_valid": True}

    for validator in [
        lambda: _check_basic_format(email_address, result),
        lambda: _check_domain(email_address, result),
        lambda: _check_blacklist_and_uniqueness(
            email_address, check_uniqueness, result
        ),
    ]:
        error_result = validator()
        if error_result:
            return error_result

    return result


def _invalid_result(result: dict, error_message: str) -> dict:
    """Helper function to format an invalid result"""
    result["error"] = error_message
    result["is_valid"] = False
    return result
