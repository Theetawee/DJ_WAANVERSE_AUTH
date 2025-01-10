from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from dj_waanverse_auth.services.mfa_service import MFAHandler


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login. Supports login via email, username, or phone number.
    Handles MFA validation and provides detailed error messages.
    """

    login_field = serializers.CharField(
        write_only=True,
        required=True,
        error_messages={
            "required": _("Please provide your email, username, or phone number."),
            "blank": _("Login field cannot be blank."),
        },
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        error_messages={
            "required": _("Password is required."),
            "blank": _("Password cannot be blank."),
            "min_length": _("Password must be at least 8 characters long."),
        },
    )

    def validate_login_field(self, value):
        """
        Validate login field format based on type (email/phone/username).
        """
        if not value:
            raise serializers.ValidationError(
                _("Login field cannot be empty."), code="required"
            )

        return value

    def validate(self, attrs):
        """
        Validate login credentials and authenticate the user.
        Handles MFA validation and account status checks.
        """
        login_field = attrs.get("login_field")
        password = attrs.get("password")
        request = self.context.get("request")

        # Authenticate user
        user = authenticate(
            request=self.context.get("request"),
            login_field=login_field,
            password=password,
        )

        if not user:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [_("Invalid login credentials.")],
                },
                code="authentication",
            )

        self._validate_account_status(user)
        login_method = request.login_method
        mfa_manager = MFAHandler(user)
        mfa_enabled = mfa_manager.is_mfa_enabled()

        attrs.update(
            {
                "user": user,
                "login_method": login_method,
                "mfa": mfa_enabled,
            }
        )

        return attrs

    def _validate_account_status(self, user):
        """
        Validate various account status conditions.
        """
        if not user.is_active:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [_("This account is inactive.")],
                },
                code="inactive_account",
            )
