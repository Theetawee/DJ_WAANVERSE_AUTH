from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication as Head
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from django.db.models import Q

User = get_user_model()


class CustomAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(
                Q(username=username) | Q(email=username) | Q(phone=username)
            )
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class JWTAuthentication(Head):
    def authenticate(self, request):
        # Try to get the token from the Authorization header
        auth = super().authenticate(request)
        if auth is not None:
            return auth

        # If no token is found in the header, try to get it from cookies
        access_token = request.COOKIES.get(
            settings.BROWSER_CONFIG["ACCESS_COOKIE_NAME"]
        )
        if access_token:
            try:
                validated_token = self.get_validated_token(access_token)
                user = self.get_user(validated_token)
                return (user, validated_token)
            except AuthenticationFailed as e:
                raise e

        return None
