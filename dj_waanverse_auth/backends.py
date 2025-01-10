from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q

User = get_user_model()


class AuthenticationBackend(BaseBackend):
    """
    Custom authentication backend that allows users to log in using
    email, phone number, or username. Stores the login method in the
    request object instead of returning it directly.
    """

    def _determine_login_method(self, login_field, matched_user):
        """
        Helper method to determine which login method was used based on the
        login field and matched user.

        Returns:
            str: One of 'email', 'phone', or 'username'
        """
        try:
            validate_email(login_field)
            if login_field == matched_user.email_address:
                return "email"
        except ValidationError:
            if login_field == matched_user.phone_number:
                return "phone"
            elif login_field == matched_user.username:
                return "username"

        return "unknown"

    def authenticate(self, request, login_field=None, password=None, **kwargs):
        """
        Authenticate a user using email, phone number, or username.
        Stores the login method in the request object.

        Args:
            request: The request object
            login_field: The field used for login (email/phone/username)
            password: The user's password
            **kwargs: Additional arguments

        Returns:
            User: The authenticated user object or None
        """
        if not login_field or not password:
            return None

        try:
            validate_email(login_field)
            query = Q(email_address=login_field)
        except ValidationError:
            query = Q(username=login_field) | Q(phone_number=login_field)

        try:
            user = User.objects.get(query)
        except User.DoesNotExist:
            return None

        if user.check_password(password):
            if request:
                request.login_method = self._determine_login_method(login_field, user)
            return user

        return None

    def get_user(self, user_id):
        """
        Retrieve a user instance by user_id.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
