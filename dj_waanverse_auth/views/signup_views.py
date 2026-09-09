from logging import getLogger
import re
import phonenumbers
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from phonenumbers import NumberParseException
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from django.contrib.auth.password_validation import validate_password

from dj_waanverse_auth import settings as auth_config

logger = getLogger(__name__)

User = get_user_model()

MAX_IDENTIFIER_LENGTH = 255
MAX_PASSWORD_LENGTH = 128


class SignupThrottle(ScopedRateThrottle):
    """
    Scoped throttle for the signup endpoint.

    Add a "signup" entry to DRF's DEFAULT_THROTTLE_RATES, e.g.:

        REST_FRAMEWORK = {
            "DEFAULT_THROTTLE_RATES": {
                "signup": "5/hour",
            },
        }

    This throttles by IP by default (AnonRateThrottle-style cache key).
    Make sure Cloudflare (or whatever proxy sits in front of this
    service) is configured so request.META["REMOTE_ADDR"] reflects the
    real client IP and not the proxy's own address — otherwise every
    request will share one throttle bucket.
    """

    scope = "signup"


class SignupView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [SignupThrottle]

    def post(self, request):
        if auth_config.disable_signup:
            return Response(
                {"msg": "Signup is disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        parsed_payload = self._validate_signup_request(request)
        if isinstance(parsed_payload, Response):
            return parsed_payload

        identifier, password = parsed_payload
        identifier_type = self.get_identifier_type(identifier)

        handler = {
            "email": self.handle_signup_email,
            "phone": self.handle_signup_phone,
            "username": self.handle_signup_username,
        }.get(identifier_type)

        if handler:
            return handler(identifier, password)

        logger.info("Signup rejected: no matching identifier type for input.")

        return Response(
            {"msg": "Please provide a valid identifier."},
            status=status.HTTP_400_BAD_REQUEST,
        )

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
            # Two concurrent requests raced past the exists() check above.
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

    def handle_signup_username(self, username: str, password: str):
        """Validates a username and creates a user."""
        username = username.strip().lower()
        if not username:
            return Response(
                {"msg": "Username is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(username) < 3 or len(username) > 30:
            return Response(
                {"msg": "Username must be between 3 and 30 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Usernames may only contain letters, numbers, and underscores.
        if not re.fullmatch(r"[a-zA-Z0-9_]+", username):
            return Response(
                {
                    "msg": (
                        "Username can only contain letters, "
                        "numbers, and underscores."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Check blacklisted usernames.
        blacklisted_usernames = [
            username.lower() for username in (auth_config.blacklisted_usernames or [])
        ]
        if username in blacklisted_usernames:
            return Response(
                {"msg": "This username is not available."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        Account = get_user_model()
        # Check if username already exists.
        if Account.objects.filter(username__iexact=username).exists():
            return Response(
                {"msg": "Account already exists."}, status=status.HTTP_400_BAD_REQUEST
            )

        password_errors = self.validate_password_strength(
            password,
            user=Account(username=username),
        )
        if password_errors:
            return Response(
                {"msg": " ".join(password_errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                Account.objects.create_user(
                    username=username,
                    password=password,
                )
        except IntegrityError:
            logger.info("Signup race: duplicate username at create_user.")
            return Response(
                {"msg": "Account already exists."}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"msg": "Account created successfully."}, status=status.HTTP_201_CREATED
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
