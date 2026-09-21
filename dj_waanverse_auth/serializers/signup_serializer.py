from logging import getLogger
from django.core.validators import validate_email
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

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


class SignupSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        max_length=MAX_IDENTIFIER_LENGTH, write_only=True
    )
    password = serializers.CharField(
        max_length=MAX_PASSWORD_LENGTH,
        write_only=True,
        style={"input_type": "password"},
    )
    turnstile_token = serializers.CharField(
        required=False, allow_null=True, write_only=True
    )

    def __init__(self, *args, **kwargs):
        # Dynamically context-inject request information if passed
        self.request = kwargs.get("context", {}).get("request")
        super().__init__(*args, **kwargs)

    def validate_identifier(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Identifier is required.")
        return value

    def validate(self, data):
        # 1. Cloudflare Turnstile Check
        if auth_config.turnstile_enabled:
            token = data.get("turnstile_token")
            remote_ip = (
                getattr(self.request, "client_ip", None) if self.request else None
            )
            if not verify_turnstile_token(token, remote_ip=remote_ip):
                raise serializers.ValidationError(
                    {"turnstile_token": "Turnstile verification failed."}
                )

        identifier = data["identifier"]
        password = data["password"]
        identifier_type = get_identifier_type(identifier)

        # 2. Process Route Specific validations
        if identifier_type == "email":
            data.update(self._validate_email_flow(identifier, password))
        elif identifier_type == "phone":
            data.update(self._validate_phone_flow(identifier, password))
        else:
            logger.info("Signup rejected: no matching identifier type for input.")
            raise serializers.ValidationError(
                {"identifier": "Please provide a valid identifier."}
            )

        return data

    def _validate_email_flow(self, email: str, password: str) -> dict:
        try:
            validate_email(email)
        except ValidationError:
            raise serializers.ValidationError(
                {"identifier": "Invalid email address format."}
            )

        email = email.strip().lower()
        domain = email.split("@")[-1]

        # Domain restrictions
        if auth_config.allowed_email_domains and domain not in [
            d.lower() for d in auth_config.allowed_email_domains
        ]:
            raise serializers.ValidationError({"identifier": "Invalid email domain."})
        if email in [e.lower() for e in (auth_config.blacklisted_emails or [])]:
            raise serializers.ValidationError(
                {"identifier": "This email address is blocked from registration."}
            )
        if domain in [d.lower() for d in (auth_config.blacklisted_email_domains or [])]:
            raise serializers.ValidationError(
                {"identifier": "This email domain is blocked from registration."}
            )

        if User.objects.filter(email_address__iexact=email).exists():
            raise serializers.ValidationError({"identifier": "Account already exists."})

        # Password rules
        self._validate_password_strength(password, user=User(email_address=email))

        return {"email_address": email, "registration_type": "email"}

    def _validate_phone_flow(self, phone: str, password: str) -> dict:
        try:
            phone_number, phone_region = normalize_phone(phone)
        except ValueError as exc:
            raise serializers.ValidationError({"identifier": str(exc)})

        if User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError({"identifier": "Account already exists."})

        self._validate_password_strength(password, user=User(phone_number=phone_number))

        return {
            "phone_number": phone_number,
            "phone_region": phone_region,
            "registration_type": "phone",
        }

    def _validate_password_strength(self, password: str, user=None):
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})

    def additional_fields(self, validated_data) -> dict:
        """
        Hook for subclasses to provide additional user fields.

        Returns:
            dict: Additional fields to pass to User.objects.create_user().
        """
        return {}

    def create(self, validated_data):
        validated_data.pop("identifier", None)
        validated_data.pop("turnstile_token", None)

        password = validated_data.pop("password")
        registration_type = validated_data.pop("registration_type")

        validated_data.update(self.additional_fields(validated_data))

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    password=password,
                    **validated_data,
                )
                return {"user": user, "registration_type": registration_type}

        except IntegrityError:
            logger.info(f"Signup race: duplicate {registration_type} at create_user.")
            raise serializers.ValidationError(
                {"non_field_errors": "Account already exists."}
            )
