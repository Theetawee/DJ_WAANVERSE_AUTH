from rest_framework import serializers

from dj_waanverse_auth.models import UserSession


class SessionSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserSession
        fields = [
            "id",
            "session_id",
            "user_agent",
            "ip_address",
            "created_at",
            "last_used",
            "is_active",
        ]
