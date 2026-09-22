# tests/test_login_view.py
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from dj_waanverse_auth.models import Session
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache
from tests.utils import generate_rsa_keypair_files

Account = get_user_model()

VIEW_MODULE = "dj_waanverse_auth.views.login_views"
KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"


class LoginViewTests(TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        private_path, public_path = generate_rsa_keypair_files(Path(self._tmp.name))

        self.patchers = [
            patch(f"{KEYS_MODULE}.private_key_path", private_path),
            patch(f"{KEYS_MODULE}.public_key_path", public_path),
        ]
        for p in self.patchers:
            p.start()
        clear_key_cache()

        self.url = reverse("dj_waanverse_auth_login")
        self.password = "StrongPassword123!"

        self.active_account = Account.objects.create_user(
            email_address="wave@example.com",
            password=self.password,
            is_active=True,
        )

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        clear_key_cache()
        self._tmp.cleanup()

    def login(self, identifier, password=None, mobile=False):
        headers = {"HTTP_X_CLIENT_TYPE": "mobile"} if mobile else {}
        return self.client.post(
            self.url,
            {
                "identifier": identifier,
                "password": password if password is not None else self.password,
            },
            content_type="application/json",
            **headers,
        )

    # ------------------------------------------------------------------
    # Basic validation
    # ------------------------------------------------------------------

    def test_requires_identifier(self):
        response = self.client.post(
            self.url, {"password": self.password}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_password(self):
        response = self.client.post(
            self.url,
            {"identifier": "wave@example.com"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_blank_identifier(self):
        response = self.login("   ")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_empty_password(self):
        response = self.login("wave@example.com", password="")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_overlong_identifier(self):
        response = self.login("a" * 300 + "@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_overlong_password(self):
        response = self.login("wave@example.com", password="a" * 200)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Success — email
    # ------------------------------------------------------------------

    def test_correct_email_credentials_log_in(self):
        response = self.login("wave@example.com")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["msg"], "Login successful.")

    def test_email_login_is_case_insensitive(self):
        response = self.login("WAVE@EXAMPLE.COM")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # Success — phone
    # ------------------------------------------------------------------

    def test_correct_phone_credentials_log_in(self):
        Account.objects.create_user(
            email_address=None,
            phone_number="+256700123456",
            phone_region="UG",
            password=self.password,
            is_active=True,
        )
        response = self.login("+256700123456")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # Failure cases — all generic, all indistinguishable
    # ------------------------------------------------------------------

    def test_wrong_password_generic_error(self):
        response = self.login("wave@example.com", password="WrongPassword123!")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["msg"], "Invalid identifier or password.")

    def test_nonexistent_account_generic_error(self):
        response = self.login("nobody@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["msg"], "Invalid identifier or password.")

    def test_unrecognized_identifier_shape_generic_error(self):
        response = self.login("just-some-text")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["msg"], "Invalid identifier or password.")

    def test_wrong_password_and_nonexistent_account_return_identical_response(self):
        wrong_password_response = self.login(
            "wave@example.com", password="WrongPassword123!"
        )
        nonexistent_response = self.login("nobody@example.com")

        self.assertEqual(
            wrong_password_response.status_code, nonexistent_response.status_code
        )
        self.assertEqual(
            wrong_password_response.data["msg"], nonexistent_response.data["msg"]
        )

    def test_failed_login_does_not_create_session_or_cookies(self):
        response = self.login("wave@example.com", password="WrongPassword123!")

        self.assertEqual(Session.objects.count(), 0)
        self.assertNotIn("access_token", response.cookies)

    # ------------------------------------------------------------------
    # Unverified accounts
    # ------------------------------------------------------------------

    def test_inactive_account_rejected_with_verify_message(self):
        Account.objects.create_user(
            email_address="pending@example.com",
            password=self.password,
            is_active=False,
        )
        response = self.login("pending@example.com")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["msg"], "Please verify your account before logging in."
        )

    def test_inactive_account_wrong_password_gets_generic_error_not_verify_message(
        self,
    ):
        """
        Verification status should only be revealed to someone who
        already proved they know the password — not to anyone
        probing with a wrong one.
        """
        Account.objects.create_user(
            email_address="pending@example.com",
            password=self.password,
            is_active=False,
        )
        response = self.login("pending@example.com", password="WrongPassword123!")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["msg"], "Invalid identifier or password.")

    def test_inactive_account_does_not_issue_tokens(self):
        Account.objects.create_user(
            email_address="pending@example.com",
            password=self.password,
            is_active=False,
        )
        response = self.login("pending@example.com")

        self.assertEqual(Session.objects.count(), 0)
        self.assertNotIn("access_token", response.cookies)

    # ------------------------------------------------------------------
    # Tokens / cookies / sessions
    # ------------------------------------------------------------------

    def test_successful_login_sets_auth_cookies(self):
        response = self.login("wave@example.com")

        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        self.assertTrue(response.cookies["access_token"]["httponly"])
        self.assertTrue(response.cookies["refresh_token"]["httponly"])

    def test_successful_login_creates_session(self):
        self.assertEqual(Session.objects.count(), 0)

        self.login("wave@example.com")

        self.assertEqual(Session.objects.count(), 1)
        session = Session.objects.get()
        self.assertEqual(session.account_id, self.active_account.pk)

    def test_each_login_creates_a_new_session(self):
        self.login("wave@example.com")
        self.login("wave@example.com")

        self.assertEqual(Session.objects.filter(account=self.active_account).count(), 2)

    def test_web_client_response_body_excludes_raw_tokens(self):
        response = self.login("wave@example.com")

        self.assertNotIn("access_token", response.data)
        self.assertNotIn("refresh_token", response.data)

    def test_mobile_client_response_body_includes_raw_tokens(self):
        response = self.login("wave@example.com", mobile=True)

        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn(
            "access_token", response.cookies
        )  # cookies set regardless of client type

    # ------------------------------------------------------------------
    # Disallowed HTTP methods
    # ------------------------------------------------------------------

    def test_rejects_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
