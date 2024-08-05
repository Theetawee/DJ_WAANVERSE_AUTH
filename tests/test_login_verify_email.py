from .test_setup import TestSetup
from rest_framework import status
from dj_waanverse_auth.settings import accounts_config
from django.core.mail import outbox


class LoginViewTests(TestSetup):

    def test_login_verify_email(self):
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
        self.assertEqual(len(outbox), 1)
        self.assertIn("Verify your email", outbox[0].subject)
        self.assertIn("test@example.com", outbox[0].to)

        # Check response data
        self.assertIn("email", response.data)
        self.assertIn("status", response.data)
        self.assertEqual(response.data["status"], "unverified")
        self.assertEqual(response.data["email"], "test@example.com")

        print(outbox)
