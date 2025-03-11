from datetime import datetime
from typing import Dict, Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_slug

from dj_waanverse_auth import settings

User = get_user_model()


class UsernameValidator:
    def __init__(self, username: str, check_uniqueness: bool = False):
        self.username = username
        self.check_uniqueness = check_uniqueness
        self.result = {"username": username, "error": None, "is_valid": True}

    def validate(self) -> Dict[str, Optional[str]]:
        """
        Validates the username using Django's built-in validator and additional custom checks.
        """
        for validator in [
            self._check_basic_format,
            self._check_length,
            self._check_blacklist_and_uniqueness,
        ]:
            if not validator():
                return self.result
        return self.result

    def _check_basic_format(self) -> bool:
        """Check if the username has a valid format"""
        if not self.username:
            return self._invalid_result(
                "Username is required. Please provide a valid username."
            )

        try:
            validate_slug(self.username)
        except ValidationError:
            return self._invalid_result(
                "Invalid username format. Ensure it only contains lowercase letters, numbers, hyphens, and underscores, with no spaces."
            )

        return True

    def _check_length(self) -> bool:
        """Check if the username length is within allowed limits"""
        if len(self.username) < settings.username_min_length:
            return self._invalid_result(
                f"Your username must be at least {settings.username_min_length} characters long."
            )

        if len(self.username) > settings.username_max_length:
            return self._invalid_result(
                f"Your username must not exceed {settings.username_max_length} characters."
            )

        return True

    def _check_blacklist_and_uniqueness(self) -> bool:
        """Check if the username is blacklisted or already in use"""
        if self.username.lower() in settings.reserved_usernames:
            return self._invalid_result(
                "This username is not allowed. Please choose a different one."
            )

        if (
            self.check_uniqueness
            and User.objects.filter(username__iexact=self.username).exists()
        ):
            return self._invalid_result(
                "This username is already taken. Please select a unique username."
            )

        return True

    def _invalid_result(self, error_message: str) -> bool:
        """Helper function to format an invalid result"""
        self.result["error"] = error_message
        self.result["is_valid"] = False
        return False


def generate_username():
    timestamp = datetime.now().strftime("%m%d%H%M%S%f")[:-3]
    return f"user{timestamp}"
