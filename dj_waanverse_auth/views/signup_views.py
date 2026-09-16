from logging import getLogger
from django.core.validators import validate_email

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.contrib.auth.password_validation import validate_password
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.utils.security.turnstile import verify_turnstile_token
from dj_waanverse_auth.utils.identifiers import (
    get_identifier_type,
    normalize_phone,
)

logger = getLogger(__name__)

User = get_user_model()

MAX_IDENTIFIER_LENGTH = 255
MAX_PASSWORD_LENGTH = 128


class SignupView(APIView):
    permission_classes = [AllowAny]
    # throttle_classes = [SignupIdentifierThrottle, SignupIPThrottle]

    def post(self, request):
        if auth_config.disable_signup:
            return Response(
                {"msg": "Something went wrong. Please try again later."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if auth_config.turnstile_enabled:
            turnstile_error = self._validate_turnstile(request)
            if turnstile_error is not None:
                return turnstile_error

        parsed_payload = self._validate_signup_request(request)
        if isinstance(parsed_payload, Response):
            return parsed_payload

        identifier, password = parsed_payload
        identifier_type = get_identifier_type(identifier)

        handler = {
            "email": self.handle_signup_email,
            "phone": self.handle_signup_phone,
        }.get(identifier_type)

        if handler:
            return handler(identifier, password)

        logger.info("Signup rejected: no matching identifier type for input.")

        return Response(
            {"msg": "Please provide a valid identifier."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _validate_turnstile(self, request):
        """
        Verifies the Cloudflare Turnstile token when Turnstile is
        enabled. Returns a Response on failure, or None to continue.
        """

        token = request.data.get("turnstile_token")

        if not isinstance(token, str):
            token = None

        if not verify_turnstile_token(
            token,
            remote_ip=getattr(request, "client_ip", None),
        ):
            return Response(
                {"msg": "Turnstile verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return None

    def _validate_signup_request(self, request):
        identifier = request.data.get("identifier")
        password = request.data.get("password")

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

        if not isinstance(identifier, str) or not isinstance(password, str):
            return Response(
                {"msg": "Invalid request payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(identifier) > MAX_IDENTIFIER_LENGTH:
            return Response(
                {"msg": "Identifier is too long."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(password) > MAX_PASSWORD_LENGTH:
            return Response(
                {"msg": "Password is too long."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        identifier = identifier.strip()
        if not identifier:
            return Response(
                {"msg": "Identifier is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return identifier, password

    @staticmethod
    def validate_password_strength(password: str, user=None):
        """
        Runs the project's configured password validators
        (AUTH_PASSWORD_VALIDATORS) against the supplied password.

        `user` should be an unsaved instance of the user model,
        populated with whatever identifier fields are already known,
        so validators like UserAttributeSimilarityValidator can
        compare the password against them.

        Returns a list of human-readable error messages. An empty
        list means the password passed all configured validators.
        """

        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            return list(exc.messages)

        return []

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

        if allowed_domains and domain not in allowed_domains:
            return Response(
                {"msg": "Invalid email domain."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if email in blacklisted_emails:
            return Response(
                {"msg": "This email address is blocked from registration."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if domain in blacklisted_domains:
            return Response(
                {"msg": "This email domain is blocked from registration."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Account = get_user_model()

        if Account.objects.filter(email_address__iexact=email).exists():
            return Response(
                {"msg": "Account already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        password_errors = self.validate_password_strength(
            password,
            user=Account(email_address=email),
        )
        if password_errors:
            return Response(
                {"msg": " ".join(password_errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                Account.objects.create_user(
                    email_address=email,
                    password=password,
                )
        except IntegrityError:
            logger.info("Signup race: duplicate email at create_user.")
            return Response(
                {"msg": "Account already exists."},
                status=status.HTTP_400_BAD_REQUEST,
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
            phone_number, phone_region = normalize_phone(phone)
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

        password_errors = self.validate_password_strength(
            password,
            user=Account(phone_number=phone_number),
        )
        if password_errors:
            return Response(
                {"msg": " ".join(password_errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                Account.objects.create_user(
                    phone_number=phone_number,
                    phone_region=phone_region,
                    password=password,
                )
        except IntegrityError:
            logger.info("Signup race: duplicate phone number at create_user.")
            return Response(
                {"msg": "Account already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"msg": "Account created successfully."},
            status=status.HTTP_201_CREATED,
        )
