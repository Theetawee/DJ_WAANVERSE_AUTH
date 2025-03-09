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

    def perform_post_creation_tasks(self, user):

        return super().perform_post_creation_tasks(user)


class PhoneSerializer(PhoneNumberVerificationSerializer):
    def _send_code(self, phone_number, code):
        print(f"This code is sent to user code:{code} on {phone_number}")
