import re
from typing import Dict, Optional

from django.contrib.auth import get_user_model

from dj_waanverse_auth import settings

User = get_user_model()


class PhoneNumberValidator:
    def __init__(self, phone_number: str, check_uniqueness: bool = False):
        phone_number = phone_number.strip().replace(" ", "").replace("-", "")
        self.phone_number = phone_number
        self.check_uniqueness = check_uniqueness
        self.result = {"phone_number": phone_number, "error": None, "is_valid": True}

    def validate(self) -> Dict[str, Optional[str]]:
        """
        Validates the phone number with custom checks.
        """
        for validator in [
            self._check_format,
            self._check_length,
            self._check_blacklist_and_uniqueness,
        ]:
            if not validator():
                return self.result
        return self.result

    def _check_format(self) -> bool:
        """Check if the phone number has a valid format"""
        if not self.phone_number:
            return self._invalid_result(
                "Phone number is required. Please provide a valid phone number."
            )

        # Using regex for phone number format (adjust according to your region's format)
        phone_regex = r"^\+?[1-9]\d{1,14}$"
        if not re.match(phone_regex, self.phone_number):
            return self._invalid_result(
                "Invalid phone number format. Ensure it starts with a '+' followed by the country code and digits only."
            )

        return True

    def _check_length(self) -> bool:
        """Check if the phone number length is within allowed limits"""
        if len(self.phone_number) > 15:
            return self._invalid_result("Phone number must not exceed 15 characters.")

        return True

    def _check_blacklist_and_uniqueness(self) -> bool:
        """Check if the phone number is blacklisted or already in use"""
        if self.phone_number in settings.blacklisted_phone_numbers:
            return self._invalid_result(
                "This phone number is not allowed. Please use a different one."
            )

        if (
            self.check_uniqueness
            and User.objects.filter(phone_number=self.phone_number).exists()
        ):
            return self._invalid_result(
                "This phone number is already in use. Please provide a different phone number."
            )

        return True

    def _invalid_result(self, error_message: str) -> bool:
        """Helper function to format an invalid result"""
        self.result["error"] = error_message
        self.result["is_valid"] = False
        return False
