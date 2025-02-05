import re
from typing import Any, Dict, Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    MinimumLengthValidator,
    NumericPasswordValidator,
    UserAttributeSimilarityValidator,
)
from django.core.validators import EmailValidator

from dj_waanverse_auth import settings


class ValidateData:
    def __init__(self):
        self.email_validator = EmailValidator()
        self.min_username_length = settings.username_min_length
        self.max_username_length = settings.username_max_length
        self.min_password_length = 8

        # Compile regex patterns
        self.username_pattern = re.compile(r"^[a-zA-Z0-9_.-]+$")
        self.password_special_chars = re.compile(r'[!@#$%^&*(),.?":{}|<>]')
        self.password_uppercase = re.compile(r"[A-Z]")
        self.password_lowercase = re.compile(r"[a-z]")
        self.password_numbers = re.compile(r"[0-9]")

    def validate_email(self, email: str, check_uniqueness=False) -> Dict[str, Any]:
        """
        Validates email using both Django's validator and custom rules.
        Returns a dictionary with validation results.
        """
        result = {"value": None, "is_valid": False, "errors": []}

        if not email:
            result["errors"].append("Email is required")
            return result

        email = email.strip().lower()

        try:
            self.email_validator(email)
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                result["errors"].append("Invalid email format")
                return result

            self._check_email_domain(email, result)
            self._check_email_length(email, result)

            if check_uniqueness:
                self._check_email_uniqueness(email, result)

        except Exception as e:
            result["errors"].append(f"Email validation failed: {str(e)}")
            return result

        if not result["errors"]:
            result["is_valid"] = True
            result["value"] = email

        return result

    def _check_email_domain(self, email: str, result: Dict[str, Any]):
        domain = email.split("@")[1]
        if email in settings.blacklisted_emails:
            result["errors"].append("Email address is not allowed")
        if domain in settings.disposable_email_domains:
            result["errors"].append("Email addresses are not allowed")

    def _check_email_length(self, email: str, result: Dict[str, Any]):
        if len(email) > 254:
            result["errors"].append("Email is too long")

    def _check_email_uniqueness(self, email: str, result: Dict[str, Any]):
        User = get_user_model()
        if User.objects.filter(email_address=email).exists():
            result["errors"].append("Email address is already in use")

    def _check_username_length(self, username: str, result: Dict[str, Any]) -> None:
        if len(username) < self.min_username_length:
            result["errors"].append(
                f"Username must be at least {self.min_username_length} characters long"
            )
        if len(username) > self.max_username_length:
            result["errors"].append(
                f"Username cannot be longer than {self.max_username_length} characters"
            )

    def _check_username_pattern(self, username: str, result: Dict[str, Any]) -> None:
        if not self.username_pattern.match(username):
            result["errors"].append(
                "Username can only contain letters, numbers, underscores, dots, and hyphens"
            )

    def _check_username_special_chars(
        self, username: str, result: Dict[str, Any]
    ) -> None:
        if username.startswith((".", "_", "-")):
            result["errors"].append("Username cannot start with a special character")
        if username.endswith((".", "_", "-")):
            result["errors"].append("Username cannot end with a special character")
        if ".." in username or "__" in username or "--" in username:
            result["errors"].append(
                "Username cannot contain consecutive special characters"
            )

    def validate_username(
        self, username: str, check_uniqueness=False
    ) -> Dict[str, Any]:
        """
        Validates username against defined rules.
        Returns a dictionary with validation results.
        """
        result = {"value": None, "is_valid": False, "errors": []}

        if not username:
            result["errors"].append("Username is required")
            return result

        username = username.strip()

        if username in settings.reserved_usernames:
            result["errors"].append("Username cannot be used")

        self._check_username_length(username, result)
        self._check_username_pattern(username, result)
        self._check_username_special_chars(username, result)

        if check_uniqueness:
            self._check_username_uniqueness(username, result)

        if not result["errors"]:
            result["is_valid"] = True
            result["value"] = username

        return result

    def _check_username_uniqueness(self, username: str, result: Dict[str, Any]):
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            result["errors"].append("Username is already in use")

    def _check_django_validators(self, password: str, username: Optional[str]) -> list:
        errors = []
        validators = [
            MinimumLengthValidator(self.min_password_length),
            CommonPasswordValidator(),
            NumericPasswordValidator(),
        ]

        if username:
            validators.append(UserAttributeSimilarityValidator())

        for validator in validators:
            try:
                validator.validate(password)
            except Exception as e:
                errors.extend(e.messages if hasattr(e, "messages") else [str(e)])

        return errors

    def _check_custom_password_rules(self, password: str) -> list:
        errors = []

        if not self.password_uppercase.search(password):
            errors.append("Password must contain at least one uppercase letter")

        if not self.password_lowercase.search(password):
            errors.append("Password must contain at least one lowercase letter")

        if not self.password_numbers.search(password):
            errors.append("Password must contain at least one number")

        if not self.password_special_chars.search(password):
            errors.append("Password must contain at least one special character")

        if len(password) > 128:
            errors.append("Password is too long (maximum 128 characters)")

        return errors

    def validate_password(
        self,
        password: str,
        username: Optional[str] = None,
        confirmation_password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validates password strength using both Django validators and custom rules.
        Returns a dictionary with validation results.
        """
        result = {"value": None, "is_valid": False, "errors": []}

        if not password:
            result["errors"].append("Password is required")
            return result
        if confirmation_password:
            if password != confirmation_password:
                result["errors"].append("Passwords do not match")
        django_errors = self._check_django_validators(password, username)
        custom_errors = self._check_custom_password_rules(password)

        result["errors"].extend(django_errors)
        result["errors"].extend(custom_errors)

        if not result["errors"]:
            result["is_valid"] = True
            result["value"] = password

        return result
