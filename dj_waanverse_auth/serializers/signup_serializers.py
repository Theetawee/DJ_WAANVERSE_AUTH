import logging

from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from dj_waanverse_auth import settings
from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth.security.utils import generate_code
from dj_waanverse_auth.services.email_service import EmailService
from dj_waanverse_auth.validators import (
    EmailValidator,
    PasswordValidator,
    PhoneNumberValidator,
    UsernameValidator,
)

logger = logging.getLogger(__name__)

Account = get_user_model()


class SignupSerializer(serializers.Serializer):
    """
    Serializer for user registration with comprehensive validation.
    """

    username = serializers.CharField(required=False)

    email_address = serializers.EmailField(required=False)

    phone_number = serializers.CharField(required=False)

    password = serializers.CharField(required=True)

    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        """
        Validate data.
        """
        username = attrs.get("username", None)

        email = attrs.get("email_address", None)
        phone_number = attrs.get("phone_number", None)
        password = attrs.get("password", None)
        confirm_password = attrs.get("confirm_password", None)
        if username is None and email is None and phone_number is None:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        _("Please provide a username, email, or phone number.")
                    ]
                }
            )
        if username:
            username = self._validate_username(username)
        if email:
            email = self._validate_email(email)
        if phone_number:
            phone_number = self._validate_phone_number(phone_number)

        password = self._validate_password(password, confirm_password)
        return attrs

    def create(self, validated_data):
        """
        Create a new user with transaction handling.
        """
        additional_fields = self.get_additional_fields(validated_data)

        user_data = {
            "password": validated_data["password"],
            **additional_fields,
        }
        if validated_data.get("username"):
            user_data["username"] = validated_data["username"]
        if validated_data.get("email_address"):
            user_data["email_address"] = validated_data["email_address"]
        if validated_data.get("phone_number"):
            user_data["phone_number"] = validated_data["phone_number"]
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

    def _validate_email(self, email):
        """
        Validate email with comprehensive checks and sanitization.
        """
        email_validation = EmailValidator(
            email_address=email, check_uniqueness=True
        ).validate()
        if email_validation.get("is_valid") is False:
            raise serializers.ValidationError(email_validation["error"])

        return email

    def _validate_password(self, password, confirm_password):
        """
        Validate password with comprehensive checks and sanitization.
        """
        password_validation = PasswordValidator(
            password=password, confirm_password=confirm_password
        ).validate()
        if password_validation.get("is_valid") is False:
            raise serializers.ValidationError(password_validation["error"])

        return password

    def _validate_phone_number(self, phone_number):
        """
        Validate phone number with comprehensive checks and sanitization.
        """
        phone_number_validation = PhoneNumberValidator(
            phone_number=phone_number, check_uniqueness=True
        ).validate()
        if phone_number_validation.get("is_valid") is False:
            raise serializers.ValidationError(phone_number_validation["error"])

        return phone_number

    def _validate_username(self, username):
        """
        Validate username with comprehensive checks and sanitization.
        """
        username_validation = UsernameValidator(
            username=username, check_uniqueness=True
        ).validate()
        if username_validation.get("is_valid") is False:
            raise serializers.ValidationError(username_validation["error"])

        return username


class EmailVerificationSerializer(serializers.Serializer):
    email_address = serializers.EmailField(
        required=True,
    )

    def __init__(self, instance=None, data=None, **kwargs):
        self.email_service = EmailService()
        self.validator = EmailValidator()
        super().__init__(instance=instance, data=data, **kwargs)

    def validate_email_address(self, email_address):
        """
        Validate email with comprehensive checks and sanitization.
        """
        email_validation = self.validator.validate_email(
            email_address, check_uniqueness=True
        )
        if email_validation.get("is_valid") is False:
            raise serializers.ValidationError(email_validation["errors"])

        return email_address

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                email_address = validated_data["email_address"]
                verification_code = VerificationCode.objects.filter(
                    email_address=email_address
                )
                if verification_code.exists():
                    verification_code.delete()
                code = generate_code(
                    length=settings.email_verification_code_length,
                    is_alphanumeric=settings.email_verification_code_is_alphanumeric,
                )
                new_verification = VerificationCode.objects.create(
                    email_address=email_address, code=code
                )
                new_verification.save()
                self.email_service.send_verification_email(email_address, code=code)
                return email_address
        except Exception as e:
            logger.error(f"Email verification failed: {str(e)}")
            raise serializers.ValidationError(
                _("Failed to initiate email verification.")
            )


class ActivateEmailSerializer(serializers.Serializer):
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
                email_address=email_address, code=code
            )

            if verification.is_expired():
                verification.delete()
                raise serializers.ValidationError({"code": "code_expired"})
            data["verification"] = verification
            return data

        except VerificationCode.DoesNotExist:
            raise serializers.ValidationError({"code": "invalid_code"})

    def create(self, validated_data):
        """
        Mark the verification code as used and verified.
        """
        with transaction.atomic():
            user = self.context.get("request").user
            email_address = validated_data["email_address"]
            verification = validated_data["verification"]
            verification.delete()
            user.email_address = email_address
            user.email_verified = True
            user.save()

        return True


class PhoneNumberVerificationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^\+?[1-9]\d{1,14}$",
                message="Enter a valid phone number in E.164 format (e.g., +1234567890).",
            )
        ],
    )

    def validate_phone_number(self, value):
        """
        Ensure the phone number is unique and not already used for verification.
        """
        if Account.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(_("This phone number is already in use."))
        return value

    def create(self, validated_data):
        """
        Create and send a verification code for the provided phone number.
        """
        try:
            with transaction.atomic():
                phone_number = validated_data["phone_number"]

                VerificationCode.objects.filter(phone_number=phone_number).delete()

                code = generate_code(
                    length=settings.email_verification_code_length,
                    is_alphanumeric=settings.email_verification_code_is_alphanumeric,
                )

                new_verification = VerificationCode.objects.create(
                    phone_number=phone_number, code=code
                )
                new_verification.save()

                self._send_code(phone_number, code)

                return {
                    "phone_number": phone_number,
                    "message": _("Verification code sent."),
                }
        except Exception as e:
            logger.error(f"Phone number verification failed: {str(e)}")
            raise serializers.ValidationError(
                _("Failed to initiate phone verification.")
            )

    def _send_code(self, phone_number, code):
        """
        Implement the logic to send the verification code via SMS or other means.
        """
        logger.info(f"Sending verification code {code} to {phone_number}")


class ActivatePhoneSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    code = serializers.CharField(required=True)

    def validate(self, data):
        """
        Validate the phone_number and code combination.
        """
        phone_number = data["phone_number"]
        code = data["code"]

        try:
            verification = VerificationCode.objects.get(
                phone_number=phone_number, code=code
            )

            if verification.is_expired():
                verification.delete()
                raise serializers.ValidationError({"code": "code_expired"})
            data["verification"] = verification
            return data

        except VerificationCode.DoesNotExist:
            raise serializers.ValidationError({"code": "invalid_code"})

    def create(self, validated_data):
        """
        Mark the verification code as used and verified.
        """
        with transaction.atomic():
            user = self.context.get("request").user
            phone_number = validated_data["phone_number"]
            verification = validated_data["verification"]
            verification.delete()
            user.phone_number = phone_number
            user.phone_number_verified = True
            user.save()

        return True
