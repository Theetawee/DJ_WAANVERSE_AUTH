from dj_waanverse_auth import settings
from phonenumbers import NumberParseException
import phonenumbers
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


def is_email_identifier(identifier: str) -> bool:
    try:
        validate_email(identifier)
        return True
    except ValidationError:
        return False


def is_phone_identifier(identifier: str) -> bool:
    """
    Checks whether the identifier is a valid international
    phone number.
    """

    if not identifier.startswith("+"):
        return False

    try:
        parsed_phone = phonenumbers.parse(identifier, None)
    except NumberParseException:
        return False

    return phonenumbers.is_valid_number(parsed_phone)


def get_identifier_type(identifier: str):
    """
    Determines which enabled authentication identifier
    the supplied value represents.
    """

    enabled_identifiers = settings.authentication_identifiers

    if "email" in enabled_identifiers:
        if is_email_identifier(identifier):
            return "email"

    if "phone" in enabled_identifiers:
        if is_phone_identifier(identifier):
            return "phone"

    return None


def normalize_phone(phone: str):
    """
    Validates and normalizes a phone number.

    Phone numbers must include an international country code.
    """

    phone = phone.strip()

    if not phone.startswith("+"):
        raise ValueError("Phone number must include the country code.")

    try:
        parsed = phonenumbers.parse(phone, None)
    except NumberParseException:
        raise ValueError("Invalid phone number.")

    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("Invalid phone number.")

    phone_number = phonenumbers.format_number(
        parsed,
        phonenumbers.PhoneNumberFormat.E164,
    )

    phone_region = phonenumbers.region_code_for_number(parsed)

    return phone_number, phone_region
