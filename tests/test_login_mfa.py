from .test_setup import TestSetup
from rest_framework import status
from django.core import mail


class LoginViewTests(TestSetup):

    def test_login_mfa_unverified_email(self):

        response = self.client.post(
            self.url,
            {
                "login_field": "testuser3",
                "password": "testpassword123",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
