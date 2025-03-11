import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dj_waanverse_auth import settings as auth_settings

Account = get_user_model()


class TestSetup(TestCase):

    fixtures = [os.path.join(settings.BASE_DIR, "fixtures/users.json")]

    def setUp(self):
        auth_settings.email_threading_enabled = False
        self.login_url = reverse("dj_waanverse_auth_login")
        self.signup_url = reverse("dj_waanverse_auth_signup")

        self.initiate_password_reset_url = reverse(
            "dj_waanverse_auth_initiate_password_reset"
        )
        self.reset_new_password_url = reverse("dj_waanverse_auth_reset_password")
        self.refresh_access_token_url = reverse(
            "dj_waanverse_auth_refresh_access_token"
        )
        self.logout_url = reverse("dj_waanverse_auth_logout")
        self.get_authenticated_user_url = reverse(
            "dj_waanverse_auth_authenticated_user"
        )
        self.client = APIClient()
        self.grant_access_url = reverse(
            "dj_waanverse_auth_grant_access",
        )

        self.test_user_1 = Account.objects.get(username="test_user1")
        self.device_info_url = reverse("dj_waanverse_auth_get_device_info")
        mail.outbox = []
        return super().setUp()
