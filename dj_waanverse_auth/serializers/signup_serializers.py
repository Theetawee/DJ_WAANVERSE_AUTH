import logging
import re

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth.services.email_service import EmailService
from dj_waanverse_auth.settings import auth_config

logger = logging.getLogger(__name__)

Account = get_user_model()


class SignupSerializer(serializers.Serializer):
    """
    Serializer for user registration with comprehensive validation.
    """

    email_address = serializers.EmailField(
        required=True,
        error_messages={"required": _("Email address is required.")},
    )

    username = serializers.CharField(
        required=True,
        min_length=auth_config.username_min_length,
        max_length=30,
        validators=[
            UniqueValidator(
                queryset=Account.objects.all(),
                message=_("This username is already taken."),
            )
        ],
        error_messages={
            "required": _("Username is required."),
            "min_length": _(
                f"Username must be at least {auth_config.username_min_length} characters long."
            ),
            "max_length": _("Username cannot exceed 30 characters."),
        },
    )

    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        error_messages={"required": _("Password is required.")},
    )

    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        error_messages={"required": _("Password confirmation is required.")},
    )

    def __init__(self, *args, **kwargs):
        self.email_service = EmailService()
        super().__init__(*args, **kwargs)

    def validate_email_address(self, email_address):
        """
        Perform email-specific validation if needed.
        """
        return email_address

    def validate_username(self, username):
        """
        Validate the username with custom rules.
        """
        username = username.strip().lower()
        if len(username) < auth_config.username_min_length:
            raise serializers.ValidationError(
                _(
                    f"Username must be at least {auth_config.username_min_length} characters long."
                )
            )
        if username in auth_config.reserved_usernames:
            raise serializers.ValidationError(
                _("This username is reserved and cannot be used.")
            )
        if not re.match(r"^[a-zA-Z0-9_.-]+$", username):
            raise serializers.ValidationError(
                _(
                    "Username can only contain letters, numbers, and the characters: . - _"
                )
            )
        return username

    def validate_password(self, password):
        """
        Validate the password using Django's validators and additional rules.
        """
        try:
            password_validation.validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return password

    def validate(self, data):
        """
        Perform cross-field validation, such as matching passwords and verifying the email.
        """
        if data.get("password") != data.get("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": _("Passwords do not match.")}
            )

        try:
            verification = VerificationCode.objects.get(
                email_address=data["email_address"], is_verified=True
            )
            data["verification"] = verification
        except VerificationCode.DoesNotExist:
            raise serializers.ValidationError(
                {"email_address": _("Email address is not verified.")}
            )

        return data

    def create(self, validated_data):
        """
        Create a new user with transaction handling.
        """
        additional_fields = self.get_additional_fields(validated_data)

        user_data = {
            "email_address": validated_data["email_address"],
            "username": validated_data["username"],
            "password": validated_data["password"],
            **additional_fields,
        }

        try:
            with transaction.atomic():
                user = Account.objects.create_user(**user_data)
                validated_data["verification"].delete()
                self.perform_post_creation_tasks(user)
            return user
        except Exception as e:
            logger.error(f"User creation failed: {str(e)}")
            raise serializers.ValidationError(_("Failed to create user account."))

    def get_additional_fields(self, validated_data):
        """
        Return any additional fields needed for user creation.
        """
        return {}

    def perform_post_creation_tasks(self, user):
        """
        Perform any post-creation tasks, such as sending welcome emails.
        """
        pass


class InitiateEmailVerificationSerializer(serializers.Serializer):
    email_address = serializers.EmailField(
        required=True,
        error_messages={
            "required": _("Email is required."),
        },
        validators=[
            UniqueValidator(
                queryset=Account.objects.all(),
                message=_("email_exists"),
            )
        ],
    )

    def __init__(self, instance=None, data=None, **kwargs):
        self.email_service = EmailService()
        super().__init__(instance=instance, data=data, **kwargs)

    def validate_email_address(self, email_address):
        """
        Validate email with comprehensive checks and sanitization.
        """
        email_validation = self.email_service.validate_email(email_address)

        if email_validation.get("errors"):
            raise serializers.ValidationError(email_validation["errors"])

        return email_address

    def create(self, validated_data):
        try:
            with transaction.atomic():
                email_address = validated_data["email_address"]
                self.email_service.send_verification_email(email_address)
                return email_address
        except Exception as e:
            logger.error(f"Email verification failed: {str(e)}")
            raise serializers.ValidationError(
                _("Failed to initiate email verification.")
            )


class VerifyEmailSerializer(serializers.Serializer):
    email_address = serializers.EmailField(required=True)
    code = serializers.CharField(required=True)

    def validate(self, data):
        """
        Validate the email and code combination.
        """
        email_address = data["email_address"]
        code = data["code"]

        try:
            verification = VerificationCode.objects.get(
                email_address=email_address, code=code, is_verified=False
            )

            if verification.is_expired():
                verification.delete()
                raise serializers.ValidationError({"code": "code_expired"})

            return data

        except VerificationCode.DoesNotExist:
            raise serializers.ValidationError({"code": "invalid_code"})

    def create(self, validated_data):
        """
        Mark the verification code as used and verified.
        """
        email_address = validated_data["email_address"]
        code = validated_data["code"]

        verification = VerificationCode.objects.get(
            email_address=email_address, code=code, is_verified=False
        )
        verification.is_verified = True
        verification.verified_at = timezone.now()
        verification.save()

        return {"email_address": email_address, "verified": True}
