from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q

User = get_user_model()


class AuthenticationBackend(BaseBackend):
    """
    Custom authentication backend that allows users to log in using:
    - Verified email
    - Verified phone number
    - Username
    """

    def authenticate(self, request, login_field=None, password=None, **kwargs):
        """
        Authenticate a user using only:
        - Verified email
        - Verified phone number
        - Username

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
            query = Q(email_address=login_field, email_verified=True)
        except ValidationError:
            query = Q(phone_number=login_field, phone_number_verified=True) | Q(
                username=login_field
            )

        try:
            user = User.objects.get(query)
        except User.DoesNotExist:
            return None

        if user.check_password(password):
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
