import pyotp
from rest_framework import status

from dj_waanverse_auth.models import MultiFactorAuth
from dj_waanverse_auth.settings import accounts_config

from .test_setup import TestSetup


class TestLoginView(TestSetup):
    def test_mfa_status_not_activated(self):
        accounts_config.AUTH_METHODS = ["phone_number"]
        self.client.post(
            self.login_url,
            {"login_field": self.user.phone_number, "password": "password1"},
            format="json",
        )

        response = self.client.get(self.mfa_status_url)
        self.assertIn("mfa_status", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("recovery_codes", response.data)
        self.assertEqual(response.data["mfa_status"], False)
        self.assertEqual(len(response.data["recovery_codes"]), 0)

    def test_mfa_status_activated(self):
        accounts_config.AUTH_METHODS = ["email"]
        response = self.client.post(
            self.login_url,
            {"login_field": self.user2.email, "password": "password2"},
            format="json",
        )
        cookie = accounts_config.MFA_COOKIE_NAME
        self.assertIn(cookie, response.cookies)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies[cookie].value, str(self.user2.id))

    def test_verify_mfa(self):
        accounts_config.AUTH_METHODS = ["username"]

        self.client.post(
            self.login_url,
            {"login_field": self.user.username, "password": "password1"},
            format="json",
        )
        response = self.client.post(self.mfa_activate_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("url", response.data)
        self.assertIn("key", response.data)

        key = response.data["key"]
        totp = pyotp.TOTP(key)

        code = totp.now()
        response = self.client.post(self.mfa_verify_url, {"code": code})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("msg", response.data)
        self.assertEqual(response.data["msg"], self.messages.mfa_enabled_success)

    def test_deactivate_mfa(self):
        accounts_config.AUTH_METHODS = ["username"]

        self.client.post(
            self.login_url,
            {"login_field": self.user2.username, "password": "password2"},
            format="json",
        )
        base = MultiFactorAuth.objects.get(account=self.user2)

        totp = pyotp.TOTP(base.secret_key)
        code = totp.now()

        self.client.post(self.mfa_login_url, {"code": code})

        response = self.client.post(
            self.mfa_deactivate_url, {"code": code, "password": "password2"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("msg", response.data)
        self.assertEqual(response.data["msg"], self.messages.mfa_deactivated)

    def test_generate_tokens(self):
        accounts_config.AUTH_METHODS = ["username"]

        self.client.post(
            self.login_url,
            {"login_field": self.user2.username, "password": "password2"},
            format="json",
        )
        base = MultiFactorAuth.objects.get(account=self.user2)

        totp = pyotp.TOTP(base.secret_key)
        code = totp.now()

        self.client.post(self.mfa_login_url, {"code": code})

        response = self.client.post(self.generate_codes_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("msg", response.data)
        self.assertEqual(
            response.data["msg"], self.messages.mfa_recovery_codes_generated
        )
