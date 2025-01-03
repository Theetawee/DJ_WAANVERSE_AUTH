from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q

User = get_user_model()


class AuthenticationBackend(BaseBackend):
    """
    Custom authentication backend that allows users to log in using
    email, phone number, or username.
    """

    def authenticate(self, request, login_field=None, password=None, **kwargs):
        """
        Authenticate a user using email, phone number, or username.
        """
        try:
            validate_email(login_field)
            query = Q(email=login_field)
        except ValidationError:
            query = Q(username=login_field) | Q(phone_number=login_field)

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
