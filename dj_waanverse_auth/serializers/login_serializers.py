from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login. Supports login via email, username, or phone.
    """

    login_field = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    def validate(self, attrs):
        """
        Validate login credentials and authenticate the user.
        """
        login_field = attrs.get("login_field")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"), username=login_field, password=password
        )

        if not user:
            raise serializers.ValidationError(
                _("Invalid login credentials."),
                code="authentication",
            )

        if not user.is_active:
            raise serializers.ValidationError(
                _("This account is inactive."),
                code="authentication",
            )

        attrs["user"] = user
        return attrs
