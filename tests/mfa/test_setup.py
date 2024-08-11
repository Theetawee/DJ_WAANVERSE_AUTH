from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dj_waanverse_auth.models import EmailAddress

Account = get_user_model()


class TestSetup(TestCase):
    def setUp(self):
        self.login_url = reverse("login")
        self.activate_url = reverse("activate_mfa")
        self.mfa_status_url = reverse("mfa_status")
        self.client = APIClient()
        self.user = Account.objects.create_user(
            username="user1",
            password="password1",
            email="a@a.com",
            name="user1",
            phone_number="1234567890",
        )

        EmailAddress.objects.create(
            user=self.user, email=self.user.email, verified=True, primary=True
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
