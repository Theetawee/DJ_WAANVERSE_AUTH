from .test_setup import TestSetup
from rest_framework import status
from dj_waanverse_auth.settings import accounts_config
from django.core import mail


class LoginViewTests(TestSetup):

    def test_login_mfa(self):
        accounts_config["VERIFY_EMAIL"] = True

        response = self.client.post(
            self.url,
            {
                "login_field": "testuser3",
                "password": "testpassword123",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("mfa", response.data)
        self.assertIn(self.mfa_cookie_name, response.cookies)
        self.assertEqual(self.mfa_cookie.value, response.data["mfa"])
        self.assertEqual(self.mfa_cookie["httponly"], True)
        self.assertEqual(response.data["mfa"], self.user3.id)
