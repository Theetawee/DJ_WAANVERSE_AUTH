from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.utils import timezone
from rest_framework import status

from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth.settings import auth_config

from .test_setup import TestSetup


class TestSignup(TestSetup):
    def setUp(self):
        super().setUp()
        mail.outbox = []
        self.valid_email = "test_email@gmail.com"
        self.valid_code = "123456"
        self.expired_time = timezone.now() - timedelta(
            minutes=auth_config.verification_email_code_expiry_in_minutes + 1
        )

    def create_verification_code(self, email, code, created_at=None):
        """Helper method to create verification codes"""
        verification_code = VerificationCode.objects.create(
            email_address=email,
            code=code,
        )
        if created_at:
            verification_code.created_at = created_at
            verification_code.save()
        return verification_code

    def test_initiate_email_verification_success(self):
        """Test successful email verification initiation with valid email"""
        response = self.client.post(
            self.initiate_email_verification_url,
            {"email_address": self.valid_email},
        )

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "code_sent")
        self.assertEqual(response.data["email_address"], self.valid_email)

        # Check email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to[0], self.valid_email)
        self.assertEqual(email.subject, auth_config.verification_email_subject)
        self.assertIn("verification code", email.body.lower())

        # Check database
        verification_code = VerificationCode.objects.latest("created_at")
        self.assertEqual(verification_code.email_address, self.valid_email)
        self.assertFalse(verification_code.is_verified)
        self.assertIsNotNone(verification_code.code)
        self.assertEqual(
            len(verification_code.code), auth_config.email_verification_code_length
        )
        self.assertTrue(
            verification_code.code.isalnum()
            if auth_config.email_verification_code_is_alphanumeric
            else True
        )

    def test_initiate_email_verification_existing_email(self):
        """Test email verification initiation with existing email"""
        response = self.client.post(
            self.initiate_email_verification_url,
            {"email_address": self.test_user_1.email_address},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("email_address", response.data)
        self.assertIn("email_exists", str(response.data["email_address"][0]))

    def test_initiate_email_verification_invalid_email(self):
        """Test email verification initiation with invalid email format"""
        response = self.client.post(
            self.initiate_email_verification_url,
            {"email_address": "not_an_email"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("email_address", response.data)
        self.assertIn(
            "Enter a valid email address", str(response.data["email_address"])
        )

    def test_initiate_email_verification_blacklisted_email(self):
        """Test email verification initiation with invalid email format"""
        auth_config.blacklisted_emails = ["blacklist@gmail.com"]
        response = self.client.post(
            self.initiate_email_verification_url,
            {"email_address": "blacklist@gmail.com"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("email_address", response.data)
        self.assertIn("blacklisted_email", str(response.data["email_address"]))

    def test_initiate_email_verification_disposable_email(self):
        """Test email verification initiation with invalid email format"""
        auth_config.disposable_email_domains = ["gm.com"]
        response = self.client.post(
            self.initiate_email_verification_url,
            {"email_address": "blacklist@gm.com"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("email_address", response.data)
        self.assertIn("disposable_email", str(response.data["email_address"]))

    def test_initiate_email_verification_empty_email(self):
        """Test email verification initiation with empty email"""
        response = self.client.post(
            self.initiate_email_verification_url,
            {"email_address": ""},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("email_address", response.data)
        self.assertIn(
            "This field may not be blank", str(response.data["email_address"])
        )

    def test_initiate_email_verification_missing_email(self):
        """Test email verification initiation with missing email field"""
        response = self.client.post(
            self.initiate_email_verification_url,
            {},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_verify_email_success(self):
        """Test successful email verification with valid code"""
        verification_code = self.create_verification_code(
            self.valid_email, self.valid_code
        )

        response = self.client.post(
            self.verify_email_url,
            {
                "email_address": self.valid_email,
                "code": self.valid_code,
            },
        )

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "verified")

        # Check database
        verification_code.refresh_from_db()
        self.assertTrue(verification_code.is_verified)
        self.assertIsNotNone(verification_code.verified_at)

    def test_verify_email_invalid_code(self):
        """Test email verification with invalid code"""
        self.create_verification_code(self.valid_email, self.valid_code)

        response = self.client.post(
            self.verify_email_url,
            {
                "email_address": self.valid_email,
                "code": "999999",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", response.data)
        self.assertIn("invalid_code", str(response.data["code"]))

    def test_verify_email_expired_code(self):
        """Test email verification with expired code"""
        self.create_verification_code(
            self.valid_email, self.valid_code, created_at=self.expired_time
        )

        response = self.client.post(
            self.verify_email_url,
            {
                "email_address": self.valid_email,
                "code": self.valid_code,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", response.data)
        self.assertEqual("code_expired", response.data["code"][0])

    def test_verify_email_mismatched_email(self):
        """Test email verification with mismatched email"""
        self.create_verification_code(self.valid_email, self.valid_code)

        response = self.client.post(
            self.verify_email_url,
            {
                "email_address": "wrong@gmail.com",
                "code": self.valid_code,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", response.data)
        self.assertIn("invalid_code", str(response.data["code"]))

    @patch("dj_waanverse_auth.models.VerificationCode.objects.create")
    def test_database_error_handling(self, mock_create):
        """Test handling of database errors during verification code creation"""
        mock_create.side_effect = Exception("Database error")

        response = self.client.post(
            self.initiate_email_verification_url,
            {"email_address": self.valid_email},
        )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_signup_success(self):
        pass
