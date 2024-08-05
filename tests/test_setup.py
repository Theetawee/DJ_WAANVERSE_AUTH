from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from dj_waanverse_auth.settings import accounts_config
from dj_waanverse_auth.models import EmailAddress, MultiFactorAuth
from rest_framework import status

Account = get_user_model()


class TestSetup(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = Account.objects.create_user(
            email="test@example.com",
            username="testuser",
            name="Test User",
            password="testpassword",
            date_of_birth="1990-01-01",
            phone_number="1234567890",
        )
        self.user2 = Account.objects.create_user(
            email="test2@example.com",
            username="testuser2",
            name="Test User 2",
            password="testpassword123",
            date_of_birth="1990-01-01",
            phone_number=None,
        )
        self.user3 = Account.objects.create_user(
            email="test3@example.com",
            username="testuser3",
            name="Test User 3",
            password="testpassword123",
            date_of_birth="1990-01-01",
            phone_number=None,
        )

        MultiFactorAuth.objects.create(account=self.user3, activated=True)

        EmailAddress.objects.create(
            user=self.user2, email="test2@example.com", primary=True, verified=True
        )

        self.access_cookie_name = accounts_config["ACCESS_TOKEN_COOKIE_NAME"]
        self.refresh_cookie_name = accounts_config["REFRESH_TOKEN_COOKIE_NAME"]
        self.mfa_cookie_name = accounts_config["MFA_COOKIE_NAME"]
        self.url = reverse("login")
        return super().setUp()

    def assert_tokens_and_cookies(self, response):
        # Common assertions for both tests
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn(self.access_cookie_name, response.cookies)
        self.assertIn(self.refresh_cookie_name, response.cookies)
        self.assertNotIn(self.mfa_cookie_name, response.cookies)
        # Retrieve the cookies
        access_cookie = response.cookies[self.access_cookie_name]
        refresh_cookie = response.cookies[self.refresh_cookie_name]

        # Assert that cookies are set and have the correct attributes
        self.assertTrue(access_cookie)
        self.assertTrue(refresh_cookie)
        self.assertEqual(access_cookie["httponly"], True)
        self.assertEqual(refresh_cookie["httponly"], True)

        # Assert that the cookie values match the response data
        self.assertEqual(access_cookie.value, response.data["access_token"])
        self.assertEqual(refresh_cookie.value, response.data["refresh_token"])
