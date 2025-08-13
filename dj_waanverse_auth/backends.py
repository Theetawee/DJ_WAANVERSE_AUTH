from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from dj_waanverse_auth.models import LoginCode

User = get_user_model()


class AuthenticationBackend(BaseBackend):
    """
    Custom authentication backend for login using email + one-time code.
    """

    def authenticate(
        self,
        request,
        email_address=None,
        username=None,
        code=None,
        password=None,
        **kwargs
    ):
        if username and password:
            return super().authenticate(request, username=username, password=password)
        if not email_address:
            raise ValidationError(("Email address is required for authentication."))
        if not code:
            raise ValidationError(("Verification code is required for authentication."))

        try:
            user = User.objects.get(email_address=email_address)
        except User.DoesNotExist:
            raise ValidationError(_("No account found with that email address."))

        login_code = LoginCode.objects.filter(account=user, code=code.strip()).first()
        if not login_code:
            raise ValidationError(_("Invalid verification code."))

        if login_code.is_expired():
            login_code.delete()  # Prevent reuse of expired codes
            raise ValidationError(_("The verification code has expired."))

        # Code is valid → delete it to enforce one-time use
        login_code.delete()
        print("Authenticated user:", user)
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
