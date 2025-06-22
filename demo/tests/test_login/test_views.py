from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework import status

from dj_waanverse_auth import settings
from dj_waanverse_auth.config.settings import auth_config
from dj_waanverse_auth.models import UserSession
from dj_waanverse_auth.utils.token_utils import decode_token

from .test_setup import Setup

Account = get_user_model()


class TestLogin(Setup):

    def assert_cookie_attributes(self, cookie, expected_value, max_age=None):
        """
        Helper function to assert cookie attributes.
        """
        self.assertIsNotNone(cookie, "Cookie should not be None")
        self.assertEqual(cookie.value, expected_value, "Cookie value mismatch")
        self.assertEqual(
            cookie["secure"],
            "" if not auth_config.cookie_secure else True,
            "Secure flag mismatch",
        )
        self.assertEqual(
            cookie["httponly"], auth_config.cookie_httponly, "HttpOnly flag mismatch"
        )
        self.assertEqual(cookie["path"], auth_config.cookie_path, "Path mismatch")
        self.assertEqual(
            cookie["domain"],
            "" if not auth_config.cookie_domain else auth_config.cookie_domain,
            "Domain mismatch",
        )
        if max_age is not None:
            self.assertEqual(
                int(cookie["max-age"]), int(max_age.total_seconds()), "Max age mismatch"
            )

    def assert_response_structure(self, response, expected_username):
        """
        Helper function to assert response structure and content.
        """
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("status"), "success")

        required_fields = ["access_token", "refresh_token", "user"]
        for field in required_fields:
            self.assertIn(field, response.data, f"Missing field: {field}")

        user_data = response.data["user"]
        self.assertEqual(user_data["username"], expected_username)
        self.assertIn("id", user_data)
        self.assertIn("email_address", user_data)

    def assert_cookies_match_response(self, response):
        """
        Helper function to assert cookies match response data.
        """
        cookies = {
            "refresh": self.client.cookies.get(auth_config.refresh_token_cookie),
            "access": self.client.cookies.get(auth_config.access_token_cookie),
        }

        for cookie_name, cookie in cookies.items():
            self.assertIsNotNone(cookie, f"{cookie_name} cookie not found")

        cookie_configs = [
            {
                "cookie": cookies["refresh"],
                "value": response.data["refresh_token"],
                "max_age": auth_config.refresh_token_cookie_max_age,
            },
            {
                "cookie": cookies["access"],
                "value": response.data["access_token"],
                "max_age": auth_config.access_token_cookie_max_age,
            },
        ]

        for config in cookie_configs:
            self.assert_cookie_attributes(
                config["cookie"], config["value"], config["max_age"]
            )

    def assert_login_email(self, subject, recipient):
        """
        Helper function to assert login alert email properties
        """
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, subject)
        self.assertEqual(email.to[0], recipient)

    def test_login_with_turnstile_success(self):
        """
        Test successful login with turnstile enabled.
        """
        auth_config.cloudflare_turnstile_secret = "1x0000000000000000000000000000000AA"
        data = self.user_1_username_login_data

        data["turnstile_token"] = "XXXX.DUMMY.TOKEN.XXXX"
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_response_structure(response, "test_user1")

        self.assert_cookies_match_response(response)

    def test_login_with_turnstile_failure(self):
        """
        Test login with turnstile failure.
        """
        auth_config.cloudflare_turnstile_secret = "2x0000000000000000000000000000000AA"
        data = self.user_1_username_login_data
        data["turnstile_token"] = "XXXX.DUMMY.TOKEN.XXXX"
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_email_enabled(self):
        """
        Test successful login with email notifications enabled.
        """
        auth_config.email_threading_enabled = True
        auth_config.email_security_notifications_enabled = True

        response = self.client.post(self.login_url, self.user_1_username_login_data)

        self.assert_response_structure(response, "test_user1")
        self.assert_cookies_match_response(response)
        self.assert_login_email(
            subject=auth_config.login_alert_email_subject,
            recipient=self.test_user_1.email_address,
        )
        access_token = response.data["access_token"]
        payload = decode_token(access_token)
        session_id = payload["sid"]
        self.assertTrue(UserSession.objects.filter(id=session_id).exists())

    def test_login_missing_fields(self):
        """
        Test login with missing required fields.
        """
        test_cases = [
            {"login_field": "test_user1"},  # Missing password
            {"password": "Test@12"},  # Missing login field
            {},  # Missing both fields
        ]

        for test_data in test_cases:
            response = self.client.post(self.login_url, test_data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("django.core.mail.send_mail")
    def test_login_email_failure(self, mock_send_mail):
        """
        Test login behavior when email sending fails.
        """
        auth_config.email_threading_enabled = True
        mock_send_mail.side_effect = Exception("Email sending failed")

        response = self.client.post(self.login_url, self.user_1_email_login_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_response_structure(response, "test_user1")

    def test_login_with_email(self):
        """
        Test successful login using email address.
        """
        last_login = self.test_user_1.last_login
        response = self.client.post(self.login_url, self.user_1_email_login_data)
        self.assert_response_structure(response, "test_user1")
        self.assert_cookies_match_response(response)
        user = Account.objects.get(email_address=self.test_user_1.email_address)
        self.assertNotEqual(last_login, user.last_login)
        access_token = response.data["access_token"]
        payload = decode_token(access_token)
        session_id = payload["sid"]
        self.assertTrue(UserSession.objects.filter(id=session_id).exists())

    def test_login_with_phone(self):
        """
        Test successful login using phone number.
        """

        response = self.client.post(self.login_url, self.user_1_phone_login_data)
        self.assert_response_structure(response, "test_user1")
        self.assert_cookies_match_response(response)

    def test_login_with_username(self):
        """
        Test successful login using username.
        """
        response = self.client.post(self.login_url, self.user_1_username_login_data)

        self.assert_response_structure(response, "test_user1")
        self.assert_cookies_match_response(response)

    def test_login_unverified_email(self):
        """
        Test login with unverified email address.
        """
        self.test_user_1.email_verified = False
        self.test_user_1.save()

        response = self.client.post(self.login_url, self.user_1_email_login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.test_user_1.email_verified = True
        self.test_user_1.save()

        response = self.client.post(self.login_url, self.user_1_email_login_data)
        self.assert_response_structure(response, "test_user1")


class TestUnVerifiedUserLogin(Setup):
    def setUp(self):
        super().setUp()
        mail.outbox = []
        self.test_user_1.email_verified = False
        self.test_user_1.phone_number_verified = False
        self.test_user_1.save()

    def test_login_unverified_email(self):
        """
        Test login with unverified email address.
        """
        response = self.client.post(self.login_url, self.user_1_email_login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any(
                settings.verification_email_subject in mail.subject
                for mail in mail.outbox
            )
        )

    def test_login_unverified_phone(self):
        """
        Test login with unverified email address.
        """
        response = self.client.post(self.login_url, self.user_1_phone_login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
