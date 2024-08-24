import time

from django.core import mail
from rest_framework import status

from dj_waanverse_auth.models import EmailConfirmationCode
from dj_waanverse_auth.settings import accounts_config

from .test_setup import TestSetup


class TestVerifyEmail(TestSetup):

    def test_send_and_verify_email(self):
        mail.outbox = []
        accounts_config.AUTH_METHODS = ["email"]
        accounts_config.AUTO_RESEND_EMAIL = True
        self.client.post(
            self.login_url,
            {"login_field": self.user1.email, "password": "password1"},
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], self.user1.email)
        self.assertEqual(mail.outbox[0].subject, self.messages.verify_email_subject)
        verification_code = EmailConfirmationCode.objects.get(user=self.user1).code

        response = self.client.post(
            self.verify_email_url,
            {"email": self.user1.email, "code": verification_code},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("email", response.data)
        self.assertIn("msg", response.data)
        self.assertEqual(response.data["msg"], self.messages.status_verified)

    def test_resend_verify_email(self):
        mail.outbox = []
        accounts_config.EMAIL_THREADING_ENABLED = False
        response = self.client.post(
            self.resend_verification_email_url,
            {"email": self.user1.email},
            format="json",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], self.user1.email)
        self.assertEqual(mail.outbox[0].subject, self.messages.verify_email_subject)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["msg"], self.messages.email_sent)

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
            response.data["email"],
            [self.messages.no_account],
        )

    def test_send_and_verify_email_invalid_code(self):
        mail.outbox = []
        accounts_config.AUTH_METHODS = ["email"]
        self.client.post(
            self.login_url,
            {"login_field": self.user1.email, "password": "password1"},
        )

        verification_code = 00000

        response = self.client.post(
            self.verify_email_url,
            {"email": self.user1.email, "code": verification_code},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["msg"], [self.messages.invalid_code])
        self.assertEqual(response.data["code"], ["invalid_code"])

    def test_send_and_verify_email_expired_code(self):
        mail.outbox = []
        accounts_config.AUTH_METHODS = ["email"]
        accounts_config.AUTO_RESEND_EMAIL = True
        accounts_config.EMAIL_VERIFICATION_CODE_DURATION = 0.001
        self.client.post(
            self.login_url,
            {"login_field": self.user1.email, "password": "password1"},
        )

        verification = EmailConfirmationCode.objects.get(user=self.user1)
        time.sleep(1)
        response = self.client.post(
            self.verify_email_url,
            {"email": self.user1.email, "code": verification.code},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["msg"], [self.messages.expired_code])
        self.assertEqual(response.data["code"], ["expired_code"])
