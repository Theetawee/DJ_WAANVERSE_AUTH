from django.core import mail
from rest_framework import status

from dj_waanverse_auth.models import EmailConfirmationCode
from dj_waanverse_auth.settings import accounts_config

from .test_setup import TestSetup


class TestVerifyEmail(TestSetup):

    def test_send_and_verify_email(self):
        accounts_config.AUTH_METHODS = ["email"]
        self.client.post(
            self.login_url,
            {"login_field": self.user1.email, "password": "password1"},
        )
        self.assertTrue(len(mail.outbox) == 1)
        self.assertEqual(mail.outbox[0].to[0], self.user1.email)
        self.assertEqual(mail.outbox[0].subject, "Email Verification")

        verification_code = EmailConfirmationCode.objects.get(user=self.user1).code

        response = self.client.post(
            self.verify_email_url,
            {"email": self.user1.email, "code": verification_code},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_resend_verify_email(self):
        response = self.client.post(
            self.resend_verification_email_url,
            {"email": self.user1.email},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], self.user1.email)
        self.assertEqual(response.data["status"], "email-sent")

    def test_send_verify_email_invalid_email(self):
        response = self.client.post(
            self.resend_verification_email_url,
            {"email": "invalid_email"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["email"][0], "Enter a valid email address.")

    def test_send_email_invalid_user(self):
        response = self.client.post(
            self.resend_verification_email_url,
            {"email": "invalid_email@gmail.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["email"][0],
            "No account is associated with this email address.",
        )
