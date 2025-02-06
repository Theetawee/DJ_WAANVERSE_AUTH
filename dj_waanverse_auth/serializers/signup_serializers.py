import logging

from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from dj_waanverse_auth import settings
from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth.security.utils import generate_code
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


class EmailVerificationSerializer(serializers.Serializer):
    email_address = serializers.EmailField(
        required=True,
    )

    def __init__(self, instance=None, data=None, **kwargs):
        self.email_service = EmailService()
        self.validator = ValidateData()
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
