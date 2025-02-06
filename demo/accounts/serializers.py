from rest_framework import serializers

from dj_waanverse_auth.serializers.signup_serializers import (
    PhoneNumberVerificationSerializer,
)
from dj_waanverse_auth.serializers.signup_serializers import SignupSerializer as Base

from .models import Account


class BasicAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["username", "id", "email_address"]


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "username",
            "email",
            "phone_number",
            "profile_image",
            "date_of_birth",
        ]


class SignupSerializer(Base):
    name = serializers.CharField(
        required=True,
        max_length=50,
        error_messages={
            "required": ("First name is required."),
            "max_length": ("First name cannot exceed 50 characters."),
        },
    )

    def get_additional_fields(self, validated_data):

        return {"name": validated_data["name"]}

    def perform_post_creation_tasks(self, user):
        print("yes")
        return super().perform_post_creation_tasks(user)


class PhoneSerializer(PhoneNumberVerificationSerializer):
    def _send_code(self, phone_number, code):
        print(f"This code is sent to user code:{code} on {phone_number}")
