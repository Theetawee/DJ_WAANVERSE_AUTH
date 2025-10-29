from django.contrib.auth import get_user_model
from rest_framework import serializers
from dj_waanverse_auth.models import UserSession

Account = get_user_model()


class BasicAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id"]


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = "__all__"
