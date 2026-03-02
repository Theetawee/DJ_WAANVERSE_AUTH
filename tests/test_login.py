from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from dj_waanverse_auth.models import AccessCode
from dj_waanverse_auth import settings as auth_config
from tests.base import BaseAPITestCase

Account = get_user_model()


class LoginCodeVerifyTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("dj_waanverse_auth_login")
        self.email = "newuser@example.com"

        self.account = Account.objects.create_user(
            email_address=self.email,
            last_login=timezone.now() - timedelta(minutes=5),
        )

        AccessCode.objects.create(
            email_address=self.email,
            code="123456",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

    # ----------------------------
    # Helper
    # ----------------------------

    def _login_with_cookie_config(self, **overrides):
        for key, value in overrides.items():
            setattr(auth_config, key, value)

        response = self.client.post(
            self.url,
            {"email_address": self.email, "code": "123456"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response

    # ----------------------------
    # Core Login Test
    # ----------------------------

    def test_login_updates_last_login(self):
        first_login_time = self.account.last_login

        response = self._login_with_cookie_config()

        self.assertLoginData(response)
        self.assertAuthCookies(response)

        self.account.refresh_from_db()
        self.assertNotEqual(first_login_time, self.account.last_login)

    # ----------------------------
    # Cookie Tests (All Attributes)
    # ----------------------------

    def test_cookie_full_configuration(self):
        access_name = "custom_access"
        refresh_name = "custom_refresh"

        access_age = timedelta(minutes=10)
        refresh_age = timedelta(days=10)

        response = self._login_with_cookie_config(
            access_token_cookie=access_name,
            refresh_token_cookie=refresh_name,
            cookie_secure=True,
            cookie_httponly=True,
            cookie_samesite="Strict",
            cookie_path="/",
            cookie_domain="example.com",
            access_token_cookie_max_age=access_age,
            refresh_token_cookie_max_age=refresh_age,
        )

        # --- Cookie existence ---
        self.assertIn(access_name, response.cookies)
        self.assertIn(refresh_name, response.cookies)

        access_cookie = response.cookies[access_name]
        refresh_cookie = response.cookies[refresh_name]

        # --- Secure ---
        self.assertTrue(access_cookie["secure"])
        self.assertTrue(refresh_cookie["secure"])

        # --- HttpOnly ---
        self.assertTrue(access_cookie["httponly"])
        self.assertTrue(refresh_cookie["httponly"])

        # --- SameSite ---
        self.assertEqual(access_cookie["samesite"], "Strict")
        self.assertEqual(refresh_cookie["samesite"], "Strict")

        # --- Path ---
        self.assertEqual(access_cookie["path"], "/")
        self.assertEqual(refresh_cookie["path"], "/")

        # --- Domain ---
        self.assertEqual(access_cookie["domain"], "example.com")
        self.assertEqual(refresh_cookie["domain"], "example.com")

        # --- Max Age ---
        self.assertEqual(
            int(access_cookie["max-age"]),
            int(access_age.total_seconds()),
        )
        self.assertEqual(
            int(refresh_cookie["max-age"]),
            int(refresh_age.total_seconds()),
        )

    # ----------------------------
    # Secure Toggle Test
    # ----------------------------

    def test_cookie_secure_toggle(self):
        response = self._login_with_cookie_config(cookie_secure=False)

        access_cookie = response.cookies[auth_config.access_token_cookie]
        refresh_cookie = response.cookies[auth_config.refresh_token_cookie]

        self.assertFalse(access_cookie["secure"])
        self.assertFalse(refresh_cookie["secure"])

    # ----------------------------
    # HttpOnly Toggle Test
    # ----------------------------

    def test_cookie_httponly_toggle(self):
        response = self._login_with_cookie_config(cookie_httponly=False)

        access_cookie = response.cookies[auth_config.access_token_cookie]
        refresh_cookie = response.cookies[auth_config.refresh_token_cookie]

        self.assertFalse(access_cookie["httponly"])
        self.assertFalse(refresh_cookie["httponly"])
