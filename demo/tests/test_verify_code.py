from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth import settings


Account = get_user_model()


class VerifyCodeTestCase(APITestCase):
    """
    Tests for account verification after signup,
    including response data and cookie attributes.
    """

    def setUp(self):
        super().setUp()
        mail.outbox.clear()
        self.activate_email_address = reverse("dj_waanverse_auth_activate_email")
        self.signup_url = reverse("dj_waanverse_auth_signup")
        self.send_email_code_url = reverse(
            "dj_waanverse_auth_send_email_verification_code"
        )
        settings.cookie_domain = "localhost"

    def _assert_cookie(self, cookie, expected_max_age):
        """
        Assert common attributes of authentication cookies.
        """
        # Handle timedelta or int for max age
        if isinstance(expected_max_age, timedelta):
            expected_max_age = int(expected_max_age.total_seconds())

        self.assertEqual(cookie["path"], settings.cookie_path)
        self.assertEqual(cookie["domain"], settings.cookie_domain)
        self.assertEqual(int(cookie["max-age"]), expected_max_age)
        self.assertEqual(cookie["samesite"], settings.cookie_samesite)
        self.assertEqual(cookie["httponly"], settings.cookie_httponly)

    def assertResponse(self, response):
        """
        Assert the response contains required keys and valid cookies.
        """
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

    def test_activate_account_after_signup(self):
        """
        Ensure account activation works after signup,
        and response/cookies match expectations.
        """
        # Step 1: Sign up
        data = {"email_address": "test1@gmail.com"}
        self.client.post(self.signup_url, data)

        verification_code = VerificationCode.objects.get(
            email_address=data["email_address"]
        ).code

        # Step 2: Activate account
        activation_payload = {
            "code": verification_code,
            "email_address": data["email_address"],
            "handle": "signup",
        }
        response = self.client.post(self.activate_email_address, activation_payload)

        # Step 3: Verify status and user fields
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = Account.objects.get(email_address=data["email_address"])
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)

        # Step 4: Verify tokens and cookies
        self.assertResponse(response)

    def test_resend_email_verification_code(self):
        Account.objects.create_user(email_address="test1@gmail.com", is_active=False)
        # resend for existing account
        data = {"email_address": "test1@gmail.com"}
        self.client.post(self.send_email_code_url, data)
        self.assertEqual(len(mail.outbox), 1)

        # resend for non account
        VerificationCode.objects.all().delete()
        mail.outbox.clear()
        data = {"email_address": "test2@gmail.com"}
        response = self.client.post(self.send_email_code_url, data)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("email_address", response.data)

        # request resending too many times
        mail.outbox.clear()
        data = {"email_address": "test1@gmail.com"}
        self.client.post(self.send_email_code_url, data)
        self.client.post(self.send_email_code_url, data)
        response = self.client.post(self.send_email_code_url, data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("too_fast", response.data["error"])

        # request resend on already verified account
        Account.objects.filter(email_address=data["email_address"]).update(
            email_verified=True
        )
        mail.outbox.clear()
        data = {"email_address": "test1@gmail.com"}
        response = self.client.post(self.send_email_code_url, data)
        self.assertEqual(len(mail.outbox), 0)
