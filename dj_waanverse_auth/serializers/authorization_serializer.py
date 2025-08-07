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
