from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dj_waanverse_auth.models import EmailAddress
from dj_waanverse_auth.settings import accounts_config

Account = get_user_model()


class TestSetup(TestCase):
    def setUp(self):
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")
        self.refresh_token_url = reverse("refresh_token")
        self.resend_verification_email_url = reverse("resend_verification_email")
        self.verify_email_url = reverse("verify_email")
        self.client = APIClient()
        self.access_cookie_name = accounts_config.ACCESS_TOKEN_COOKIE
        self.refresh_cookie_name = accounts_config.REFRESH_TOKEN_COOKIE
        self.user1 = Account.objects.create_user(
            username="user1",
            password="password1",
            email="a@a.com",
            name="user1",
            phone_number="1234567890",
        )

        self.user2 = Account.objects.create_user(
            username="user2", password="password2", email="b@b.com", name="user2"
        )

        EmailAddress.objects.create(
            user=self.user2, email="b@b.com", verified=True, primary=True
        ).save()

    def assert_auth_cookies(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.access_cookie_name, response.cookies)
        self.assertIn(self.refresh_cookie_name, response.cookies)

    def assert_auth_response(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn("user", response.data)
