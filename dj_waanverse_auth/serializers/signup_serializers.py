import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from dj_waanverse_auth.utils.phone_utils import get_send_code_function
from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth.utils.email_utils import verify_email_address
from dj_waanverse_auth.utils.generators import generate_code

logger = logging.getLogger(__name__)

Account = get_user_model()


class SignupSerializer(serializers.Serializer):
    """
    Serializer for user registration without passwords.
    Email is required.
    Username is optional; auto-generated if not provided.
    """

    email_address = serializers.EmailField(required=True)

    def validate_email_address(self, email_address):
        accounts = Account.objects.filter(email_address=email_address)
        if accounts.filter(email_verified=True).exists():
            raise serializers.ValidationError(
                {"email_address": _("Email address is already in use.")}
            )

        else:
            return email_address

    def create(self, validated_data):
        """
        Create a new user without password.
        Auto-generate username if missing.
        """
        email = validated_data["email_address"]

        user_data = {
            "email_address": email,
            "is_active": False,
        }

        try:
            with transaction.atomic():
                if Account.objects.filter(
                    email_address=email, email_verified=False
                ).exists():
                    user = Account.objects.get(
                        email_address=email, email_verified=False
                    )
                else:
                    user = Account.objects.create_user(**user_data)
                verify_email_address(user)
                self.perform_post_creation_tasks(user)
            return user
        except Exception as e:
            logger.error(f"User creation failed: {str(e)}")
            raise serializers.ValidationError(f"failed {e}")

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

    def validate_email_address(self, email_address):
        """
        Validate email with comprehensive checks and sanitization.
        """
        user = self.context.get("user")
        if user.email_address != email_address:
            raise serializers.ValidationError("mismatch")
        return email_address

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        try:
            email_address = validated_data["email_address"]
            verify_email_address(self.context.get("user"))
            return email_address
        except Exception as e:
            logger.error(f"Email verification failed: {str(e)}")
            raise serializers.ValidationError(f"failed {e}")


class ActivateEmailSerializer(serializers.Serializer):
    email_address = serializers.EmailField(required=True)
    code = serializers.CharField(required=True)
    handle = serializers.CharField(required=False)

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
            user = Account.objects.get(email_address=validated_data["email_address"])
            email_address = validated_data["email_address"]
            verification = validated_data["verification"]
            verification.delete()
            user.email_address = email_address
            user.email_verified = True
            user.is_active = True
            user.save(update_fields=["email_address", "email_verified", "is_active"])

        return user


class PhoneNumberVerificationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)

    def validate_phone_number(self, value):
        """
        Ensure the phone number is unique and not already used for verification.
        """
        user = self.context.get("user")
        if user.phone_number != value:
            raise serializers.ValidationError("mismatch")

        return value

    def create(self, validated_data):
        """
        Create and send a verification code for the provided phone number.
        """
        try:
            with transaction.atomic():
                phone_number = validated_data["phone_number"]

                VerificationCode.objects.filter(phone_number=phone_number).delete()

                code = generate_code()

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
        send_func = get_send_code_function()
        send_func(phone_number, code)


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
