from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

User = get_user_model()


class AuthenticationBackend(BaseBackend):
    """
    Custom authentication backend that allows users to log in using:
    - Verified email
    - Verified phone number
    - Username
    """

    def _authenticate_email(self, login_field):
        """Authenticate using email"""
        try:
            validate_email(login_field)
        except ValidationError:
            raise ValidationError("Invalid email format.")

        user = User.objects.filter(email_address=login_field).first()
        if not user:
            raise ValidationError("No account found with this email.")
        return user

    def _authenticate_phone(self, login_field):
        """Authenticate using phone number"""
        user = User.objects.filter(phone_number=login_field).first()
        if not user:
            raise ValidationError("No account found with this phone number.")
        return user

    def _authenticate_username(self, login_field):
        """Authenticate using username"""
        user = User.objects.filter(username=login_field).first()
        if not user:
            raise ValidationError("No account found with this username.")
        return user

    def authenticate(
        self, request, login_field=None, password=None, method="username", **kwargs
    ):
        """
        Authenticate a user using only:
        - Verified email
        - Verified phone number
        - Username

        Args:
            request: The request object
            login_field: The field used for login (email/phone/username)
            password: The user's password
            method: The authentication method (email_address, phone_number, username)
            **kwargs: Additional arguments

        Returns:
            User: The authenticated user object or raises a ValidationError.
        """
        if not login_field or not password or not method:
            raise ValidationError(
                "All fields (login_field, password, method) are required."
            )

        method_map = {
            "email_address": self._authenticate_email,
            "phone_number": self._authenticate_phone,
            "username": self._authenticate_username,
        }

        auth_method = method_map.get(method.lower())
        if not auth_method:
            raise ValidationError(
                "Invalid method. Choose email_address, phone_number, or username."
            )

        user = auth_method(login_field)
        if user and user.check_password(password):
            return user

        raise ValidationError("Invalid credentials. Please try again.")

    def get_user(self, user_id):
        """
        Retrieve a user instance by user_id.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
