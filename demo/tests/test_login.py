import base64
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from dj_waanverse_auth.models import LoginCode, WebAuthnChallenge
from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth import settings

import uuid


User = get_user_model()


class AuthViewsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email_address="test@example.com",
            email_verified=True,
            is_active=True,
        )
        self.client = APIClient()
        self.login_url = reverse("dj_waanverse_auth_login")
        self.get_login_code_url = reverse("dj_waanverse_auth_get_login_code")

    def log_user_in(self):
        """Helper: issue login code and log in user."""
        LoginCode.objects.create(
            account=self.user,
            code="123456",
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        response = self.client.post(
            self.login_url, {"email_address": self.user.email_address, "code": "123456"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response

    def test_login_success_and_failures(self):
        # Wrong email
        res = self.client.post(
            self.login_url, {"email_address": "nope@example.com", "code": "123456"}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Wrong code
        LoginCode.objects.create(
            account=self.user,
            code="999999",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        res = self.client.post(
            self.login_url, {"email_address": self.user.email_address, "code": "111111"}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Correct login
        response = self.log_user_in()
        self.assertIn(auth_config.access_token_cookie, response.cookies)

        # expired code
        LoginCode.objects.all().delete()
        LoginCode.objects.create(
            account=self.user,
            code="123456",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        res = self.client.post(
            self.login_url, {"email_address": self.user.email_address, "code": "123456"}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_login_code_success_and_throttling(self):
        # No email
        res = self.client.post(self.get_login_code_url, {})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid email
        res = self.client.post(self.get_login_code_url, {"email_address": "bademail"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Nonexistent user (always returns success)
        res = self.client.post(
            self.get_login_code_url, {"email_address": "ghost@example.com"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for key in ["user", "access_token", "refresh_token", "sid"]:
            self.assertNotIn(key, res.data)

        # Valid user
        res = self.client.post(
            self.get_login_code_url, {"email_address": self.user.email_address}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Throttled (request again immediately)
        res = self.client.post(
            self.get_login_code_url, {"email_address": self.user.email_address}
        )
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class WebAuthnFlowTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email_address="flow@example.com", email_verified=True, is_active=True
        )

        self.get_passkey_registration_options_url = reverse(
            "dj_waanverse_auth_generate_registration_options"
        )

    def test_generate_registration_options_unauthenticated(self):
        response = self.client.post(
            self.get_passkey_registration_options_url,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_generate_registration_options_misconfigured(self):
        self.client.force_authenticate(self.user)
        settings.webauthn_domain = None
        settings.webauthn_rp_name = None
        settings.webauthn_origin = None
        response = self.client.post(
            self.get_passkey_registration_options_url,
            {"email_address": self.user.email_address},
        )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_generate_registration_options_authenticated(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.get_passkey_registration_options_url,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data

        # --- Top-level required fields ---
        expected_fields = [
            "rp",
            "user",
            "challenge",
            "pubKeyCredParams",
            "timeout",
            "excludeCredentials",
            "challengeId",
        ]
        for field in expected_fields:
            self.assertIn(field, data, msg=f"Missing {field} in response")

        # --- RP object ---
        self.assertEqual(data["rp"]["name"], settings.webauthn_rp_name)
        self.assertEqual(data["rp"]["id"], settings.webauthn_domain)

        user_id_bytes = str(self.user.pk).encode("utf-8")
        user_id_b64url = (
            base64.urlsafe_b64encode(user_id_bytes).rstrip(b"=").decode("utf-8")
        )
        self.assertEqual(data["user"]["id"], user_id_b64url)
        self.assertEqual(data["user"]["name"], self.user.username)
        self.assertIsNotNone(data["user"]["displayName"])

        # --- Challenge ---
        self.assertTrue(
            WebAuthnChallenge.objects.filter(
                id=data["challengeId"], user=self.user
            ).exists()
        )
        self.assertIsInstance(data["challenge"], str)
        self.assertGreater(len(data["challenge"]), 0)

        # --- pubKeyCredParams ---
        self.assertIsInstance(data["pubKeyCredParams"], list)
        # --- Timeout ---
        self.assertEqual(data["timeout"], 60000)

        if "attestation" in data:
            self.assertEqual(data["attestation"], "none")
