import logging
from django.core.validators import validate_email
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth.utils.email_utils import verify_email_address
from dj_waanverse_auth import settings

logger = logging.getLogger(__name__)

Account = get_user_model()


class SignupSerializer(serializers.Serializer):
    """
    Serializer for user registration using only email.
    """

    email_address = serializers.EmailField(required=True)

    def validate(self, attrs):
        email = attrs.get("email_address")
        self._validate_email(email)
        return attrs

    def _validate_email(self, email):
        # Check if email already exists and verified
        if Account.objects.filter(email_address=email, email_verified=True).exists():
            raise serializers.ValidationError(
                {"email_address": "Email address is already in use."}
            )

        try:
            validate_email(email)
        except Exception as e:
            raise serializers.ValidationError({"email_address": str(e)})

        # Check allowed domains
        if settings.allowed_email_domains:
            domain = email.split("@")[1]
            if domain not in settings.allowed_email_domains:
                raise serializers.ValidationError(
                    {"email_address": "Email domain is not allowed."}
                )

        if email in settings.blacklisted_emails:
            raise serializers.ValidationError(
                {"email_address": "Email address is not allowed."}
            )

    def create(self, validated_data):
        """
        Create a new user with email only.
        """
        email = validated_data.get("email_address")

        user_data = {
            "email_address": email,
            "is_active": False,
        }

        try:
            with transaction.atomic():
                # Reuse unverified existing user if present
                if Account.objects.filter(
                    email_address=email, email_verified=False
                ).exists():
                    user = Account.objects.get(
                        email_address=email, email_verified=False
                    )
                else:
                    user = Account.objects.create_user(**user_data)

                # Trigger email verification
                verify_email_address(user)

                self.perform_post_creation_tasks(user)

            return user
        except Exception as e:
            logger.error(f"User creation failed: {str(e)}")
            raise serializers.ValidationError(f"Failed to create user: {e}")

    def perform_post_creation_tasks(self, user):
        """
        Optional post-creation tasks, e.g., welcome email.
        """
        pass


class EmailVerificationSerializer(serializers.Serializer):
    email_address = serializers.EmailField(required=True)

    def validate_email_address(self, email_address):
        try:
            Account.objects.get(email_address=email_address, email_verified=False)
        except Account.DoesNotExist:
            raise serializers.ValidationError("invalid")
        return email_address

    def create(self, validated_data):
        email_address = validated_data["email_address"]
        user = Account.objects.get(email_address=email_address, email_verified=False)
        verify_email_address(
            user
        )
        return email_address


class ActivateEmailSerializer(serializers.Serializer):
    email_address = serializers.EmailField(required=True)
    code = serializers.CharField(required=True)

    def validate(self, data):
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
        with transaction.atomic():
            user = Account.objects.get(email_address=validated_data["email_address"])
            verification = validated_data["verification"]
            verification.delete()
            user.email_verified = True
            user.is_active = True
            user.save(update_fields=["email_verified", "is_active"])
        return user
