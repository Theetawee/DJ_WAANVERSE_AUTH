from django.contrib.auth import authenticate
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login. Supports login via email, username, or phone number.
    Handles MFA validation and provides detailed error messages.
    """

    email_address = serializers.EmailField(required=True)
    code = serializers.CharField(required=True)

    def validate(self, attrs):
        """
        Validate login credentials and authenticate the user.
        """

        user = authenticate(
            email_address=attrs["email_address"],
            code=attrs["code"],
        )
        if not user:
            raise serializers.ValidationError(
                {
                    "non_field_errors": ["Invalid login credentials."],
                },
                code="authentication",
            )
        self._validate_account_status(user)
        attrs.update({"user": user})
        return attrs

    def _validate_account_status(self, user):
        """
        Validate various account status conditions.
        """
        if not user.is_active:
            raise serializers.ValidationError(
                {
                    "non_field_errors": ["This account is inactive."],
                },
                code="inactive_account",
            )
