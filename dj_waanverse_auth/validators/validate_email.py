from typing import Dict, Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email

from dj_waanverse_auth import settings

User = get_user_model()


class EmailValidator:
    def __init__(self, email_address: str, check_uniqueness: bool = False):
        self.email_address = email_address
        self.check_uniqueness = check_uniqueness
        self.result = {"email": email_address, "error": None, "is_valid": True}

    def validate(self) -> Dict[str, Optional[str]]:
        """
        Validates the email address using Django's built-in validator and additional custom checks.
        """
        for validator in [
            self._check_basic_format,
            self._check_domain,
            self._check_blacklist_and_uniqueness,
        ]:
            if not validator():
                return self.result
        return self.result

    def _check_basic_format(self) -> bool:
        """Check basic email format requirements"""
        if not self.email_address:
            return self._invalid_result("Email address is required.")

        try:
            django_validate_email(self.email_address)
        except ValidationError:
            return self._invalid_result("Invalid email format.")

        if len(self.email_address) > 250:
            return self._invalid_result(
                "Email address is too long (maximum 250 characters)."
            )

        return True

    def _check_domain(self) -> bool:
        """Check domain-related validations"""
        try:
            _, domain = self.email_address.split("@", 1)
        except ValueError:
            return self._invalid_result("Invalid email format.")

        if domain in settings.disposable_email_domains:
            return self._invalid_result("Disposable email addresses are not allowed.")

        return True

    def _check_blacklist_and_uniqueness(self) -> bool:
        """Check blacklist and uniqueness validations"""
        if self.email_address.lower() in settings.blacklisted_emails:
            return self._invalid_result("This email address is not allowed.")

        if (
            self.check_uniqueness
            and User.objects.filter(email_address__iexact=self.email_address).exists()
        ):
            return self._invalid_result("Email address is already in use.")

        return True

    def _invalid_result(self, error_message: str) -> bool:
        """Helper function to format an invalid result"""
        self.result["error"] = error_message
        self.result["is_valid"] = False
        return False
