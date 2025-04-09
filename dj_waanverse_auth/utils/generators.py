import random
import string

from dj_waanverse_auth import settings


def generate_code(
    length: int = settings.email_verification_code_length,
    alphanumeric: bool = settings.email_verification_code_is_alphanumeric,
) -> str:
    """
    Generate a random verification code.

    Args:
        length (int): The length of the verification code. Default is 6.
        alphanumeric (bool): If True, includes both letters and numbers. Default is False.

    Returns:
        str: Generated verification code.
    """
    if length <= 0:
        raise ValueError("Length must be greater than 0.")

    characters = string.digits
    if alphanumeric:
        characters += string.ascii_letters

    return "".join(random.choices(characters, k=length))
