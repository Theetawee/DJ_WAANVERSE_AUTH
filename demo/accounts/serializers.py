from rest_framework import serializers

from dj_waanverse_auth.serializers import SignupSerializer as Core

from .models import Account


class BasicAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["username", "id", "email"]


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


class SignupSerializer(Core):
    name = serializers.CharField(required=True, max_length=255)

    def get_additional_fields(self, validated_data):
        return {
            "name": validated_data["name"],
        }
