from django.contrib.auth import get_user_model
from rest_framework import serializers

from dj_waanverse_auth.models import UserSession

Account = get_user_model()


class SessionSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserSession
        fields = [
            "id",
            "user_agent",
            "ip_address",
            "created_at",
            "last_used",
            "is_active",
        ]


class UpdateAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "username",
            "email_address",
            "phone_number",
            "phone_number_verified",
            "email_verified",
        ]

    def update(self, instance, validated_data):
        """
        Overriding the update method to ensure partial updates work as expected and reset `verified` if email or phone changes.
        """
        # Check if email or phone number has been changed
        if (
            "email_address" in validated_data
            and validated_data["email_address"] != instance.email_address
        ):
            validated_data["email_verified"] = False

        if (
            "phone_number" in validated_data
            and validated_data["phone_number"] != instance.phone_number
        ):
            validated_data["phone_number_verified"] = False
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
