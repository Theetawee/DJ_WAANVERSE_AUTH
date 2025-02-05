import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth.security.utils import validate_turnstile_token
from dj_waanverse_auth.security.validators import ValidateData
from dj_waanverse_auth.services.email_service import EmailService

logger = logging.getLogger(__name__)

Account = get_user_model()


class SignupSerializer(serializers.Serializer):
    """
    Serializer for user registration with comprehensive validation.
    """

    username = serializers.CharField(required=True)

    password = serializers.CharField(required=True)

    confirm_password = serializers.CharField(required=True)

    def __init__(self, *args, **kwargs):
        self.email_service = EmailService()
        self.validator = ValidateData()
        super().__init__(*args, **kwargs)

    def validate_username(self, username):
        """
        Validate username with comprehensive checks and sanitization.
        """
        username_validation = self.validator.validate_username(
            username, check_uniqueness=True
        )
        if username_validation.get("is_valid") is False:
            raise serializers.ValidationError(username_validation["errors"])

        return username

    def validate(self, attrs):
        """
        Validate password with comprehensive checks.
        """
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")
        username = attrs.get("username")
        password_validation = self.validator.validate_password(
            password, username=username, confirmation_password=confirm_password
        )
        if password_validation.get("is_valid") is False:
            raise serializers.ValidationError(password_validation["errors"])

        return attrs

    def create(self, validated_data):
        """
        Create a new user with transaction handling.
        """
        additional_fields = self.get_additional_fields(validated_data)

        user_data = {
            "username": validated_data["username"],
            "password": validated_data["password"],
            **additional_fields,
        }
        try:
            with transaction.atomic():
                user = Account.objects.create_user(**user_data)
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
    turnstile_token = serializers.CharField(required=False)

    def __init__(self, instance=None, data=None, **kwargs):
        self.email_service = EmailService()
        super().__init__(instance=instance, data=data, **kwargs)

    def validate_email_address(self, email_address):
        """
        Validate email with comprehensive checks and sanitization.
        """
        email_validation = self.email_service.validate_email(email_address)
        if email_validation.get("error"):
            raise serializers.ValidationError(email_validation["error"])

        return email_address

    def validate(self, attrs):
        turnstile_token = attrs.get("turnstile_token")

        # Validate Turnstile captcha token if provided
        if turnstile_token:
            if not validate_turnstile_token(turnstile_token):
                raise serializers.ValidationError(
                    {"turnstile_token": [_("Invalid Turnstile token.")]},
                    code="captcha_invalid",
                )

        return attrs

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
