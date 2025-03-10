from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework import status

from dj_waanverse_auth import settings
from dj_waanverse_auth.models import VerificationCode

from .setup import Setup

Account = get_user_model()


class TestSignupView(Setup):
    def setUp(self):
        super().setUp()
        settings.blacklisted_emails = ["user@example.com"]
        settings.disposable_email_domains = ["test.com"]

    def test_signup_view(self):
        data = {
            "username": {
                "username": "test_user",
                "password": "Test@1220",
                "confirm_password": "Test@1220",
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

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            expected_cookies = [
                settings.access_token_cookie,
                settings.refresh_token_cookie,
            ]
            expected_response_data = ["status", "access_token", "refresh_token"]
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
                    1,
                )
            if key == "email":
                user = Account.objects.get(email_address=value["email_address"])
                self.assertEqual(user.email_verified, False)
                self.assertEqual(response.data["next"], "verify_email")
                self.assertEqual(len(mail.outbox), 1)
                self.assertEqual(
                    mail.outbox[0].subject, settings.verification_email_subject
                )
                self.assertEqual(VerificationCode.objects.count(), 1)
            if key == "username":
                user = Account.objects.get(username=value["username"])
                self.assertEqual(user.email_verified, False)
                self.assertEqual(user.phone_number_verified, False)
                self.assertEqual(response.data["next"], None)

    def test_signup_blacklisted_email(self):
        data = {
            "password": "Test@1220",
            "confirm_password": "Test@1220",
            "email_address": "user@example.com",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["non_field_errors"][0],
            "This email address is not allowed.",
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
            response.data["non_field_errors"][0],
            "Disposable email addresses are not allowed.",
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

        code = VerificationCode.objects.get(phone_number=data["phone_number"]).code

        response = self.client.post(
            self.activate_phone_url,
            data={"phone_number": data["phone_number"], "code": code},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Account.objects.get(
                phone_number=data["phone_number"]
            ).phone_number_verified,
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

    def test_add_email(self):
        response = self.client.post(
            self.add_email_url,
            data={"email_address": "9Vz2K@example.com", "password": "Test@1220"},
        )
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Account.objects.get(email_address="9Vz2K@example.com").email_verified, False
        )
        self.assertEqual(VerificationCode.objects.count(), 1)

    def test_mark_account_status(self):
        response = self.client.post(
            self.update_account_status_url, data={"status": "completed"}
        )
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            Account.objects.get(email_address="test@example.com").is_account_completed
        )
        response = self.client.post(
            self.update_account_status_url, data={"status": "incomplete"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            Account.objects.get(email_address="test@example.com").is_account_completed
        )

        response = self.client.post(
            self.update_account_status_url, data={"status": "invalid"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            Account.objects.get(email_address="test@example.com").is_account_completed
        )

    def test_update_account(self):
        response = self.client.patch(
            self.update_account_url,
            data={
                "name": "test",
                "email_address": "test1@example.com",
                "phone_number": "1294567890",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Account.objects.get(username="test_user").name, "test")

        self.assertFalse(Account.objects.get(username="test_user").email_verified)
        self.assertFalse(
            Account.objects.get(username="test_user").phone_number_verified
        )
        self.assertEqual(
            Account.objects.get(username="test_user").email_address, "test1@example.com"
        )
        self.assertEqual(
            Account.objects.get(username="test_user").phone_number, "1294567890"
        )
