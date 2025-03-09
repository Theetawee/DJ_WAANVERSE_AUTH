from typing import Dict, Optional

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class PasswordValidator:
    def __init__(self, password: str, confirm_password: str):
        self.password = password
        self.confirm_password = confirm_password
        self.result = {"password": password, "error": None, "is_valid": True}

    def validate(self) -> Dict[str, Optional[str]]:
        """
        Validates the password using Django's built-in password validators and custom checks.
        """
        for validator in [
            self._check_basic_format,
            self._same_password,
            self._check_strength,
            self._check_length,
        ]:
            if not validator():
                return self.result

        try:
            validate_password(self.password)
        except ValidationError as e:
            return self._invalid_result(
                f"Password is not strong enough: {', '.join(e.messages)}"
            )

        return self.result

    def _same_password(self) -> bool:
        if self.password != self.confirm_password:
            return self._invalid_result("Passwords do not match.")
        return True

    def _check_basic_format(self) -> bool:
        """Ensure the password is not empty"""
        if not self.password:
            return self._invalid_result(
                "Password is required. Please provide a password."
            )
        return True

    def _check_strength(self) -> bool:
        """Ensure the password contains at least one uppercase, one lowercase, one digit, and one special character"""
        if not any(char.islower() for char in self.password):
            return self._invalid_result(
                "Password must contain at least one lowercase letter."
            )

        if not any(char.isupper() for char in self.password):
            return self._invalid_result(
                "Password must contain at least one uppercase letter."
            )

        if not any(char.isdigit() for char in self.password):
            return self._invalid_result("Password must contain at least one digit.")

        return True

    def _check_length(self) -> bool:
        """Check if the password length is within allowed limits"""
        if len(self.password) < 8:
            return self._invalid_result("Password must be at least 8 characters long.")

        return True

    def _invalid_result(self, error_message: str) -> bool:
        """Helper function to format an invalid result"""
        self.result["error"] = error_message
        self.result["is_valid"] = False
        return False
