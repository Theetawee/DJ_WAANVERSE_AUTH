import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from dj_waanverse_auth import settings
from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth.services.email_service import EmailPriority, EmailService
from dj_waanverse_auth.services.utils import generate_verification_code
from dj_waanverse_auth.validators import (
    EmailValidator,
    PasswordValidator,
    PhoneNumberValidator,
    UsernameValidator,
)

logger = logging.getLogger(__name__)

Account = get_user_model()


def verify_email_address(email_address):
    code = generate_verification_code()
    email_manager = EmailService()
    template_name = "emails/verify_email.html"
    with transaction.atomic():
        VerificationCode.objects.create(email_address=email_address, code=code)
        email_manager.send_email(
            subject=settings.verification_email_subject,
            template_name=template_name,
            recipient=email_address,
            context={"code": code},
            priority=EmailPriority.HIGH,
        )


class SignupSerializer(serializers.Serializer):
    """
    Serializer for user registration with comprehensive validation.
    """

    username = serializers.CharField(required=False)

    email_address = serializers.EmailField(required=False)

    phone_number = serializers.CharField(required=False)

    password = serializers.CharField(required=True)

    confirm_password = serializers.CharField(required=True)

    def validate_email_address(self, email_address):
        if email_address is None:
            return None
        return self._validate_email(email_address)

    def validate_username(self, username):
        if username is None:
            return None
        return self._validate_username(username)

    def validate_phone_number(self, phone_number):
        if phone_number is None:
            return None
        return self._validate_phone_number(phone_number)

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
        password = self._validate_password(password, confirm_password)
        return attrs

    def create(self, validated_data):
        """
        Create a new user with transaction handling.
        """
        additional_fields = self.get_additional_fields(validated_data)
        used_field = None
        user_data = {
            "password": validated_data["password"],
            **additional_fields,
        }
        if validated_data.get("username"):
            user_data["username"] = validated_data["username"]
            used_field = "username"
        if validated_data.get("email_address"):
            user_data["email_address"] = validated_data["email_address"]
            used_field = "email_address"
        if validated_data.get("phone_number"):
            user_data["phone_number"] = validated_data["phone_number"]
            used_field = "phone_number"
        try:
            with transaction.atomic():
                user = Account.objects.create_user(**user_data)
                if used_field:
                    if used_field == "email_address":
                        verify_email_address(user.email_address)
                    if used_field == "phone_number":
                        self._verify_phone_number(user.phone_number)
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
        phone_number = phone_number_validation["phone_number"]
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

    def _verify_phone_number(self, phone_number):
        code = generate_verification_code()
        existing_verification = VerificationCode.objects.filter(
            phone_number=phone_number
        )
        if existing_verification.exists():
            existing_verification.delete()
        VerificationCode.objects.create(phone_number=phone_number, code=code)
        self._send_phone_code(phone_number, code)

    def _send_phone_code(self, phone_number, code):
        pass


class EmailVerificationSerializer(serializers.Serializer):
    email_address = serializers.EmailField(
        required=True,
    )

    def validate_email_address(self, email_address):
        """
        Validate email with comprehensive checks and sanitization.
        """
        check_uniqueness = True
        is_resend = self.context.get("is_resend", False)
        if is_resend:
            check_uniqueness = False

        email_validation = EmailValidator(
            email_address=email_address, check_uniqueness=check_uniqueness
        ).validate()
        if email_validation.get("is_valid") is False:
            raise serializers.ValidationError(email_validation["error"])

        return email_address

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                user = self.context.get("user")
                email_address = validated_data["email_address"]
                verification_code = VerificationCode.objects.filter(
                    email_address=email_address
                )
                if verification_code.exists():
                    verification_code.delete()
                verify_email_address(email_address)
                user.email_address = email_address
                user.email_verified = False
                user.save()
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
            user.save(update_fields=["email_address", "email_verified"])

        return True


class PhoneNumberVerificationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)

    def validate_phone_number(self, value):
        """
        Ensure the phone number is unique and not already used for verification.
        """
        check_uniqueness = True
        is_resend = self.context.get("is_resend", False)
        if is_resend:
            check_uniqueness = False
        validation = PhoneNumberValidator(
            value, check_uniqueness=check_uniqueness
        ).validate()
        if validation.get("is_valid") is False:
            raise serializers.ValidationError(validation["error"])

        return value

    def create(self, validated_data):
        """
        Create and send a verification code for the provided phone number.
        """
        try:
            with transaction.atomic():
                phone_number = validated_data["phone_number"]

                VerificationCode.objects.filter(phone_number=phone_number).delete()

                code = generate_verification_code()

                new_verification = VerificationCode.objects.create(
                    phone_number=phone_number, code=code
                )
                new_verification.save()
                user = self.context.get("user")
                user.phone_number = phone_number
                user.phone_number_verified = False
                user.save(update_fields=["phone_number", "phone_number_verified"])

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
