from logging import getLogger

import phonenumbers
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from phonenumbers import NumberParseException
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from dj_waanverse_auth import settings as auth_config

logger = getLogger(__name__)


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if auth_config.disable_signup:
            return Response(
                {"msg": "Signup is disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        identifier = request.data.get("identifier", None)
        password = request.data.get("password", None)

        if not identifier:
            return Response(
                {"msg": "Identifier is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not password:
            return Response(
                {"msg": "Password is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        identifier = identifier.strip()

        identifier_type = self.get_identifier_type(identifier)

        if identifier_type == "email":
            return self.handle_signup_email(
                email=identifier,
                password=password,
            )

        if identifier_type == "phone":
            return self.handle_signup_phone(
                phone=identifier,
                password=password,
            )

        if identifier_type == "username":
            return self.handle_signup_username(
                username=identifier,
                password=password,
            )

        return Response(
            {"msg": "Please provide a valid identifier."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def get_identifier_type(self, identifier: str):
        """
        Determines which enabled authentication identifier
        the supplied value represents.
        """

        enabled_identifiers = auth_config.authentication_identifiers

        # Check email first.
        if "email" in enabled_identifiers:
            if self._is_email_identifier(identifier):
                return "email"

        # Check phone next.
        if "phone" in enabled_identifiers:
            if self._is_phone_identifier(identifier):
                return "phone"

        # Username is the fallback because usernames do not have
        # a strict format like email addresses or phone numbers.
        if "username" in enabled_identifiers:
            return "username"

        return None

    def handle_signup_email(self, email: str, password: str):
        """
        Validates an email and creates a user.
        """

        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {"msg": "Invalid email address format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = email.strip().lower()
        domain = email.split("@")[-1]

        allowed_domains = [
            domain.lower() for domain in (auth_config.allowed_email_domains or [])
        ]

        blacklisted_emails = [
            email.lower() for email in (auth_config.blacklisted_emails or [])
        ]

        blacklisted_domains = [
            domain.lower() for domain in (auth_config.blacklisted_email_domains or [])
        ]

        # Allowed domains
        if allowed_domains and domain not in allowed_domains:
            return Response(
                {"msg": "Invalid email domain."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Blacklisted email
        if email in blacklisted_emails:
            return Response(
                {"msg": ("This email address is blocked from registration.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Blacklisted domain
        if domain in blacklisted_domains:
            return Response(
                {"msg": ("This email domain is blocked from registration.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Account = get_user_model()

        if Account.objects.filter(email_address__iexact=email).exists():
            return Response(
                {"msg": "Account already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Account.objects.create_user(
            email_address=email,
            password=password,
        )

        return Response(
            {"msg": "Account created successfully."},
            status=status.HTTP_201_CREATED,
        )

    def handle_signup_phone(self, phone: str, password: str):
        """
        Validates a phone number and creates a user.

        Phone numbers must include their country code.
        Example: +256700000000
        """

        try:
            phone_number, phone_region = self.normalize_phone(phone)

        except ValueError as exc:
            return Response(
                {"msg": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Account = get_user_model()

        if Account.objects.filter(phone_number=phone_number).exists():
            return Response(
                {"msg": "Account already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Account.objects.create_user(
            phone_number=phone_number,
            phone_region=phone_region,
            password=password,
        )

        return Response(
            {"msg": "Account created successfully."},
            status=status.HTTP_201_CREATED,
        )

    def handle_signup_username(self, username: str, password: str):
        """
        Validates a username and creates a user.
        """

        username = username.strip()

        if not username:
            return Response(
                {"msg": "Username is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Account = get_user_model()

        if Account.objects.filter(username__iexact=username).exists():
            return Response(
                {"msg": "Account already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Account.objects.create_user(
            username=username,
            password=password,
        )

        return Response(
            {"msg": "Account created successfully."},
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
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

    @staticmethod
    def _is_email_identifier(identifier: str) -> bool:
        try:
            validate_email(identifier)
            return True

        except ValidationError:
            return False

    @staticmethod
    def _is_phone_identifier(identifier: str) -> bool:
        """
        Checks whether the identifier is a valid international
        phone number.
        """

        if not identifier.startswith("+"):
            return False

        try:
            parsed_phone = phonenumbers.parse(
                identifier,
                None,
            )

        except NumberParseException:
            return False

        return phonenumbers.is_valid_number(parsed_phone)
