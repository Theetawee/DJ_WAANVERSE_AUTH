from rest_framework import serializers
from .models import Account
from dj_waanverse_auth.serializers import SignupSerializer as Core


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
            "pronouns",
            "custom_pronouns",
        ]


class SignupSerializer(Core):
    name = serializers.CharField(required=True, max_length=255)
    date_of_birth = serializers.DateField(required=True)
    pronouns = serializers.ChoiceField(choices=Account.PRONOUNS, required=True)
    custom_pronouns = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )

    def get_additional_fields(self, validated_data):
        return {
            "name": validated_data["name"],
            "date_of_birth": validated_data["date_of_birth"],
            "pronouns": validated_data["pronouns"],
        }
