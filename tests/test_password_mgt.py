from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from rest_framework import status

from dj_waanverse_auth.models import ResetPasswordToken
from dj_waanverse_auth.config.settings import auth_config

from .test_setup import TestSetup

Account = get_user_model()


class ResetPasswordTokenTests(TestSetup):
    def setUp(self):
        super().setUp()

        mail.outbox = []
        self.token = ResetPasswordToken.create_for_user(self.test_user_1)

    def test_token_generation(self):
        token = ResetPasswordToken.create_for_user(self.test_user_1)
        self.assertIsNotNone(token.code)
        self.assertEqual(token.account, self.test_user_1)

    def test_token_expiration(self):
        token = ResetPasswordToken.create_for_user(self.test_user_1)

        # Test non-expired token
        self.assertFalse(token.is_expired())

        # Test expired token
        token.created_at = timezone.now() - timedelta(
            minutes=auth_config.password_reset_expiry_in_minutes + 1
        )
        token.save()
        self.assertTrue(token.is_expired())

    def test_used_token(self):
        token = ResetPasswordToken.create_for_user(self.test_user_1)
        token.use_token()
        self.assertTrue(token.is_used)
        self.assertTrue(token.is_expired())

    def test_successful_reset_initiation(self):
        response = self.client.post(
            self.initiate_password_reset_url,
            {"email_address": self.test_user_1.email_address},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.test_user_1.email_address])
        self.assertEqual(
            mail.outbox[0].subject, auth_config.password_reset_email_subject
        )
        self.assertTrue(
            ResetPasswordToken.objects.filter(account=self.test_user_1).exists()
        )

    def test_invalid_email(self):
        response = self.client.post(
            self.initiate_password_reset_url, {"email_address": "invalid-email"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_email(self):
        response = self.client.post(
            self.initiate_password_reset_url,
            {"email_address": "nonexistent@example.com"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(
            ResetPasswordToken.objects.filter(
                account__email_address="nonexistent@example.com"
            ).exists()
        )

    def test_successful_password_reset(self):
        response = self.client.post(
            self.reset_new_password_url,
            {
                "email_address": self.test_user_1.email_address,
                "code": self.token.code,
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.test_user_1.refresh_from_db()
        self.assertTrue(self.test_user_1.check_password("NewPassword123!"))

        self.token.refresh_from_db()
        self.assertTrue(self.token.is_used)

    def test_mismatched_passwords(self):
        response = self.client.post(
            self.reset_new_password_url,
            {
                "email_address": self.test_user_1.email_address,
                "code": self.token.code,
                "new_password": "NewPassword123!",
                "confirm_password": "DifferentPassword123!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password(self):
        response = self.client.post(
            self.reset_new_password_url,
            {
                "email_address": self.test_user_1.email_address,
                "code": self.token.code,
                "new_password": "weak",
                "confirm_password": "weak",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_token(self):
        response = self.client.post(
            self.reset_new_password_url,
            {
                "email_address": self.test_user_1.email_address,
                "code": "invalid-token",
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_token(self):
        self.token.created_at = timezone.now() - timedelta(
            minutes=auth_config.password_reset_expiry_in_minutes + 1
        )
        self.token.save()

        response = self.client.post(
            self.reset_new_password_url,
            {
                "email_address": self.test_user_1.email_address,
                "code": self.token.code,
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_used(self):
        self.token.use_token()

        response = self.client.post(
            self.reset_new_password_url,
            {
                "email_address": self.test_user_1.email_address,
                "code": self.token.code,
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
