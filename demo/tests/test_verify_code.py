from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from django.utils import timezone
from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth import settings

Account = get_user_model()


class VerifyCodeTestCase(APITestCase):
    """
    Tests for account verification after signup,
    including activation, resend, expired codes, and cookie checks.
    """

    def setUp(self):
        super().setUp()
        mail.outbox.clear()
        self.signup_url = reverse("dj_waanverse_auth_signup")
        self.activate_email_address = reverse("dj_waanverse_auth_activate_email")
        self.active_phone_number = reverse("dj_waanverse_auth_activate_phone")
        self.send_email_code_url = reverse(
            "dj_waanverse_auth_send_email_verification_code"
        )
        self.send_phone_code_url = reverse(
            "dj_waanverse_auth_send_phone_number_verification_code"
        )
        settings.cookie_domain = "localhost"

    # ----- Helper Methods -----
    def _assert_cookie(self, cookie, expected_max_age):
        if isinstance(expected_max_age, timedelta):
            expected_max_age = int(expected_max_age.total_seconds())
        self.assertEqual(cookie["path"], settings.cookie_path)
        self.assertEqual(cookie["domain"], settings.cookie_domain)
        self.assertEqual(int(cookie["max-age"]), expected_max_age)
        self.assertEqual(cookie["samesite"], settings.cookie_samesite)
        self.assertEqual(cookie["httponly"], settings.cookie_httponly)

    def assertResponse(self, response):
        expected_keys = ["access_token", "refresh_token", "user"]
        for key in expected_keys:
            self.assertIn(key, response.data)

        cookies_to_check = [
            (settings.access_token_cookie, settings.access_token_cookie_max_age),
            (settings.refresh_token_cookie, settings.refresh_token_cookie_max_age),
        ]
        for cookie_name, max_age in cookies_to_check:
            with self.subTest(cookie=cookie_name):
                self.assertIn(cookie_name, response.cookies)
                self._assert_cookie(response.cookies[cookie_name], max_age)

    def _create_account(self, email=None, phone=None, verified=False, active=False):
        return Account.objects.create_user(
            email_address=email,
            phone_number=phone,
            email_verified=verified,
            phone_number_verified=verified,
            is_active=active,
        )

    def _send_verification_request(self, url, data):
        mail.outbox.clear()
        return self.client.post(url, data)

    def _test_resend_verification(self, url, field_name, account_value):
        """Generic test logic for resending verification codes."""
        # Existing unverified account
        self._create_account(
            email=account_value if field_name == "email_address" else None,
            phone=account_value if field_name == "phone_number" else None,
            active=False,
        )
        response = self._send_verification_request(url, {field_name: account_value})
        if field_name == "email_address":
            self.assertEqual(len(mail.outbox), 1)

        # Non-existent account
        VerificationCode.objects.all().delete()
        response = self._send_verification_request(url, {field_name: "nonexistent"})
        self.assertIn(field_name, response.data)

        # Request too fast
        for _ in range(2):
            self._send_verification_request(url, {field_name: account_value})
        response = self._send_verification_request(url, {field_name: account_value})
        self.assertIn("too_fast", response.data["error"])

        # Already verified
        Account.objects.filter(**{field_name: account_value}).update(
            email_verified=True if field_name == "email_address" else False,
            phone_number_verified=True if field_name == "phone_number" else False,
        )
        response = self._send_verification_request(url, {field_name: account_value})
        if field_name == "email_address":
            self.assertEqual(len(mail.outbox), 0)
        else:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ----- Tests -----
    def test_activate_account_after_signup_email(self):
        data = {"email_address": "test1@gmail.com"}
        self.client.post(self.signup_url, data)
        verification_code = VerificationCode.objects.get(
            email_address=data["email_address"]
        ).code

        payload = {
            "code": verification_code,
            "email_address": data["email_address"],
            "handle": "signup",
        }
        response = self.client.post(self.activate_email_address, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = Account.objects.get(email_address=data["email_address"])
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertResponse(response)

    def test_activate_account_after_signup_phone(self):
        data = {"phone_number": "+256779820542"}
        self.client.post(self.signup_url, data)
        verification_code = VerificationCode.objects.get(
            phone_number=data["phone_number"]
        ).code

        payload = {
            "code": verification_code,
            "phone_number": data["phone_number"],
            "handle": "signup",
        }
        response = self.client.post(self.active_phone_number, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = Account.objects.get(phone_number=data["phone_number"])
        self.assertTrue(user.is_active)
        self.assertTrue(user.phone_number_verified)
        self.assertResponse(response)

    def test_resend_email_verification_code(self):
        self._test_resend_verification(
            self.send_email_code_url, "email_address", "test1@gmail.com"
        )

    def test_resend_phone_verification_code(self):
        self._test_resend_verification(
            self.send_phone_code_url, "phone_number", "+256779820542"
        )

    def test_activate_expired_email_code(self):
        data = {"email_address": "test1@gmail.com"}
        self.client.post(self.signup_url, data)

        verification_code = VerificationCode.objects.get(
            email_address=data["email_address"]
        )

        print(verification_code.created_at)

        # Set created_at to more than 5 minutes ago to simulate expiry
        verification_code.created_at = timezone.now() + timedelta(minutes=20)
        verification_code.save()

        print(verification_code.created_at)

        payload = {
            "code": verification_code.code,
            "email_address": data["email_address"],
            "handle": "signup",
        }

        response = self.client.post(self.activate_email_address, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code_expired", response.data["error"])
