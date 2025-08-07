from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework import status

from dj_waanverse_auth import settings
from dj_waanverse_auth.models import UserSession, VerificationCode
from dj_waanverse_auth.utils.token_utils import decode_token
from dj_waanverse_auth.throttles import (
    EmailVerificationThrottle,
    PhoneVerificationThrottle,
)

from .setup import Setup

Account = get_user_model()


class TestDisableSignUp(Setup):

    def setUp(self):
        super().setUp()
        settings.blacklisted_emails = ["user@example.com"]
        settings.disposable_email_domains = ["test.com"]
        settings.disable_signup = True

    def test_disable_signup(self):
        """
        Test the IPBlockerMiddleware to ensure it blocks the correct IP addresses
        and allows the correct IP addresses.
        """
        data = {
            "username": "test_user",
            "password": "Test@1220",
            "confirm_password": "Test@1220",
            "phone_number": "1234567870",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestSignupView(Setup):
    def setUp(self):
        super().setUp()
        settings.blacklisted_emails = ["user@example.com"]
        settings.disposable_email_domains = ["test.com"]
        settings.disable_signup = False

    def test_signup_view(self):
        data = {
            "username": {
                "username": "test_user",
                "password": "Test@1220",
                "confirm_password": "Test@1220",
                "phone_number": "1234567870",
            },
            "email": {
                "email_address": "9Vz2K@example.com",
                "password": "Test@1220",
                "confirm_password": "Test@1220",
            },
            "phone_number": {
                "phone_number": "1234567890",
                "password": "Test@1220",
                "confirm_password": "Test@1220",
            },
        }

        for key, value in data.items():
            response = self.client.post(self.signup_url, value)
            access_token = response.data["access_token"]
            payload = decode_token(access_token)
            session_id = payload["sid"]
            self.assertTrue(UserSession.objects.filter(id=session_id).exists())
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            expected_cookies = [
                settings.access_token_cookie,
                settings.refresh_token_cookie,
            ]
            expected_response_data = ["status", "access_token", "refresh_token", "user"]
            for cookie_name in expected_cookies:
                self.assertIn(cookie_name, response.cookies)

            for field in expected_response_data:
                self.assertIn(field, response.data)

            if key == "phone_number":
                user = Account.objects.get(phone_number=value["phone_number"])
                self.assertEqual(response.data["next"], "verify_phone")
                self.assertEqual(user.phone_number_verified, False)
                self.assertTrue(
                    VerificationCode.objects.filter(
                        phone_number=user.phone_number
                    ).exists()
                )
                self.assertTrue(
                    VerificationCode.objects.filter(
                        phone_number=user.phone_number
                    ).count(),
                    2,
                )

                self.assertIsNotNone(user.username)
            if key == "email":
                user = Account.objects.get(email_address=value["email_address"])
                self.assertEqual(user.email_verified, False)
                self.assertEqual(response.data["next"], "verify_email")
                self.assertEqual(len(mail.outbox), 1)
                self.assertEqual(
                    mail.outbox[0].subject, settings.verification_email_subject
                )
                self.assertEqual(VerificationCode.objects.count(), 2)
                self.assertIsNotNone(user.username)

            if key == "username":
                user = Account.objects.get(username=value["username"])
                self.assertEqual(user.email_verified, False)
                self.assertEqual(user.phone_number_verified, False)
                self.assertEqual(response.data["next"], "verify_phone")
                self.assertEqual(user.username, value["username"])

    @patch.object(EmailVerificationThrottle, "allow_request", return_value=True)
    def test_signup_confirm_send_email_already_exists(self, _):
        data = {
            "email_address": "9Vz2K@example.com",
            "password": "Test@1220",
            "confirm_password": "Test@1220",
        }
        self.client.post(self.signup_url, data)

        # now resend verification code
        response = self.client.post(
            self.verify_email_address_url, {"email_address": "9Vz2K@example.com"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch.object(EmailVerificationThrottle, "allow_request", return_value=True)
    def test_signup_confirm_resend_email(self, _):
        data = {
            "email_address": "9Vz2K@example.com",
            "password": "Test@1220",
            "confirm_password": "Test@1220",
        }
        self.client.post(self.signup_url, data)

        # now resend verification code
        response = self.client.post(
            self.verify_email_address_url,
            {"email_address": "9Vz2K@example.com", "type": "resend"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch.object(PhoneVerificationThrottle, "allow_request", return_value=True)
    def test_signup_confirm_resend_phone(self, _):
        data = {
            "phone_number": "1234567890",
            "password": "Test@1220",
            "confirm_password": "Test@1220",
        }
        self.client.post(self.signup_url, data)

        # now resend verification code
        response = self.client.post(
            self.send_phone_verification_code_url,
            {"phone_number": "1234567890", "type": "resend"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_signup_blacklisted_email(self):
        data = {
            "password": "Test@1220",
            "confirm_password": "Test@1220",
            "email_address": "user@example.com",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["email_address"][0],
            "email_not_allowed",
        )

    def test_signup_disposable_email(self):
        data = {
            "password": "Test@1220",
            "confirm_password": "Test@1220",
            "email_address": "user@test.com",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["email_address"][0],
            "disposable_email",
        )

    def test_signup_short_password(self):
        data = {
            "password": "Test@12",
            "confirm_password": "Test@12",
            "email_address": "9Vz2K@example.com",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["non_field_errors"][0],
            "Password must be at least 8 characters long.",
        )

    def test_signup_password_mismatch(self):
        data = {
            "password": "Test@1220",
            "confirm_password": "Test@1221",
            "email_address": "9Vz2K@example.com",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["non_field_errors"][0],
            "Passwords do not match.",
        )

    def test_signup_invalid_email(self):
        data = {
            "password": "Test@1220",
            "confirm_password": "Test@1220",
            "email_address": "test",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["email_address"][0],
            "Enter a valid email address.",
        )

    def test_verify_email(self):
        data = {
            "password": "Test@1220",
            "confirm_password": "Test@1220",
            "email_address": "9Vz2Ko@example.com",
        }
        self.client.post(self.signup_url, data)

        code = VerificationCode.objects.get(email_address="9Vz2Ko@example.com").code

        response = self.client.post(
            self.activate_email_url,
            data={"email_address": "9Vz2Ko@example.com", "code": code},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Account.objects.get(email_address="9Vz2Ko@example.com").email_verified,
            True,
        )
        self.assertEqual(VerificationCode.objects.count(), 0)

    def test_verify_phone(self):
        data = {
            "password": "Test@1220",
            "confirm_password": "Test@1220",
            "phone_number": "+911234567890",
        }
        self.client.post(self.signup_url, data)
        phone_number = data["phone_number"].replace("+", "")
        code = VerificationCode.objects.get(phone_number=phone_number).code

        response = self.client.post(
            self.activate_phone_url,
            data={"phone_number": phone_number, "code": code},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Account.objects.get(phone_number=phone_number).phone_number_verified,
            True,
        )
        self.assertEqual(VerificationCode.objects.count(), 0)


class TestVerifications(Setup):
    def setUp(self):
        super().setUp()
        account = Account.objects.create_user(
            username="test_user",
            email_address="test@example.com",
            password="Test@1220",
            email_verified=True,
            phone_number="1234567890",
            phone_number_verified=True,
        )
        account.save()
        self.account = account
        self.client.force_authenticate(user=account)

    def test_add_phone(self):
        response = self.client.post(
            self.send_phone_verification_code_url,
            data={"phone_number": "4448883363"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("mismatch", response.data["phone_number"])
