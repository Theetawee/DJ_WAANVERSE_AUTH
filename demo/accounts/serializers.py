from rest_framework import serializers
from dj_waanverse_auth.serializers import SignupSerializer as BaseSignupSerializer
from .models import Account


class SignupSerializer(BaseSignupSerializer):

    name = serializers.CharField(
        required=True, error_messages={"required": "Name is required."}
    )

    def validate_name(self, value):
        if not value:
            raise serializers.ValidationError("Name is required.")

        if len(value) < 5:
            raise serializers.ValidationError(
                "Name must be at least 3 characters long."
            )
        return value

    def additional_fields(self, validated_data):

        return {
            "name": validated_data.get("name"),
        }


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
