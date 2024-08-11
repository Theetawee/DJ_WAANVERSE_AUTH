import re
import string

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .settings import accounts_config


def validate_username(username: str) -> tuple:
    """A function that validates the username.

    Args:
        username (str): The username to validate.

    Returns:
        tuple: A tuple containing a boolean indicating if the username is valid
            and a string containing the error message if the username is invalid.
    """
    if len(username) < accounts_config.USERNAME_MIN_LENGTH:
        return (
            False,
            f"Username should be at least {accounts_config.USERNAME_MIN_LENGTH} characters long.",
        )

    if username in accounts_config.DISALLOWED_USERNAMES:
        return False, f"Username must not contain the word '{username}'."

    # Check for allowed characters (letters, numbers, and underscores)
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username should only contain letters, numbers, and underscores."

    # Check for maximum length
    if len(username) > 30:
        return False, "Username should not exceed 30 characters."

    return True, ""


def password_validator(password, user=None):
    """
    Validates the password using Django's built-in validators and additional custom rules.
    """
    errors = []

    # Run Django's built-in password validators
    try:
        validate_password(password, user)
    except ValidationError as e:
        errors.extend(e.messages)

    # Add any additional custom validation rules
    if not any(char.isdigit() for char in password):
        errors.append(_("Password must contain at least one digit."))

    if not any(char.isupper() for char in password):
        errors.append(_("Password must contain at least one uppercase letter."))

    if not any(char.islower() for char in password):
        errors.append(_("Password must contain at least one lowercase letter."))

    if not any(char in string.punctuation for char in password):
        errors.append(
            _(
                "Password must contain at least one special character (e.g., @, #, $, etc.)."
            )
        )

    if errors:
        raise ValidationError(errors)

    return password
