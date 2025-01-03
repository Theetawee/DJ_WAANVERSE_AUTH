import logging
import re

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.db import transaction
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

    email = serializers.EmailField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=Account.objects.all(),
                message=_("This email is already registered."),
            )
        ],
        error_messages={
            "required": _("Email address is required."),
            "invalid": _("Please enter a valid email address."),
        },
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
        error_messages={
            "required": _("Password is required."),
        },
    )

    password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        error_messages={
            "required": _("Password confirmation is required."),
        },
    )

    def __init__(self, instance=None, data=None, **kwargs):
        self.email_service = EmailService()
        self._password_validators_cache = None
        super().__init__(instance=instance, data=data, **kwargs)

    def validate_email(self, email):
        """
        Validate email with comprehensive checks and sanitization.
        """
        email_validation = self.email_service.validate_email(email)

        if email_validation.get("errors"):
            raise serializers.ValidationError(email_validation["errors"])

        return email

    def validate_username(self, username):
        """
        Validate username with comprehensive checks.
        """
        try:
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

        except Exception as e:
            logger.error(f"Username validation error: {str(e)}")
            raise serializers.ValidationError(_("Invalid username format."))

    def validate_password1(self, password):
        """
        Validate password with Django's validators and additional checks.
        """
        try:
            password_validation.validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))

        return password

    def validate(self, data):
        """
        Perform cross-field validation.
        """
        try:
            if data.get("password") != data.get("password_confirm"):
                raise serializers.ValidationError(
                    {"password_confirm": _("Passwords do not match.")}
                )

            return data

        except Exception as e:
            logger.error(f"Data validation error: {str(e)}")
            raise serializers.ValidationError(_("Invalid data provided."))

    def create(self, validated_data):
        """
        Create new user with error handling and logging.
        """
        try:
            additional_fields = self.get_additional_fields(validated_data)

            user_data = {
                "email": validated_data["email"],
                "username": validated_data["username"],
                "password": validated_data["password1"],
                **additional_fields,
            }

            from django.db import transaction

            with transaction.atomic():
                user = Account.objects.create_user(**user_data)

                self.perform_post_creation_tasks(user)

            return user

        except Exception as e:
            logger.error(f"User creation failed: {str(e)}")
            raise serializers.ValidationError(_("Failed to create user account."))

    def get_additional_fields(self, validated_data):
        """
        Get additional fields for user creation. Override for custom fields.
        """
        return {}

    def perform_post_creation_tasks(self, user):
        """
        Perform any necessary tasks after user creation. Override as needed.
        """
        try:
            # Send welcome email if configured
            if auth_config.send_welcome_email:
                self.email_service.send_welcome_email(user)

            # Additional setup tasks can be added here
            pass

        except Exception as e:
            logger.error(f"Post-creation tasks failed for user {user.id}: {str(e)}")


class InitiateEmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": _("Email is required."),
        },
        validators=[
            UniqueValidator(
                queryset=Account.objects.all(),
                message=_("This email is already registered."),
            )
        ],
    )

    def __init__(self, instance=None, data=None, **kwargs):
        self.email_service = EmailService()
        super().__init__(instance=instance, data=data, **kwargs)

    def validate_email(self, email):
        """
        Validate email with comprehensive checks and sanitization.
        """
        email_validation = self.email_service.validate_email(email)

        if email_validation.get("errors"):
            raise serializers.ValidationError(email_validation["errors"])

        return email

    def create(self, validated_data):
        try:
            with transaction.atomic():
                verification_code = self.email_service.generate_verification_code()
                email = validated_data["email"]
                existing_verification = VerificationCode.objects.filter(
                    email_address=email
                ).first()
                if existing_verification:
                    existing_verification.delete()

                new_verification = VerificationCode.objects.create(
                    email_address=email, code=verification_code
                )
                new_verification.save()
                self.email_service.send_verification_email(email, verification_code)
                return email
        except Exception as e:
            logger.error(f"Email verification failed: {str(e)}")
            raise serializers.ValidationError(
                _("Failed to initiate email verification.")
            )
