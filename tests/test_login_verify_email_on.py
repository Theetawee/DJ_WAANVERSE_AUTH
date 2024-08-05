from .test_setup import TestSetup
from rest_framework import status
from dj_waanverse_auth.settings import accounts_config
from django.core import mail


class LoginViewTests(TestSetup):

    def test_login_not_verified(self):
        accounts_config["VERIFY_EMAIL"] = True

        response = self.client.post(
            self.url,
            {
                "login_field": "testuser",
                "password": "testpassword",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Email Verification")
        self.assertEqual(mail.outbox[0].to, ["test@example.com"])
        # Check response data
        self.assertIn("email", response.data)
        self.assertIn("status", response.data)
        self.assertEqual(response.data["status"], "unverified")
        self.assertEqual(response.data["email"], "test@example.com")

    def test_login_verified(self):
        accounts_config["VERIFY_EMAIL"] = True

        response = self.client.post(
            self.url,
            {
                "login_field": "testuser2",
                "password": "testpassword123",
            },
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assert_tokens_and_cookies(response)
