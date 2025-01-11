from unittest.mock import patch

from django.core import mail
from rest_framework import status

from dj_waanverse_auth.models import UserDevice
from dj_waanverse_auth.settings import auth_config

from .test_setup import TestSetup


class TestLogin(TestSetup):
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

        required_fields = ["access_token", "refresh_token", "user", "device_id"]
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
            "device": self.client.cookies.get(auth_config.device_id_cookie_name),
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
            {
                "cookie": cookies["device"],
                "value": response.data["device_id"],
                "max_age": auth_config.refresh_token_cookie_max_age,
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

    def test_login_with_email_enabled(self):
        """
        Test successful login with email notifications enabled.
        """
        auth_config.email_threading_enabled = True
        auth_config.send_login_alert_emails = True

        response = self.client.post(self.login_url, self.user_1_username_login_data)

        self.assert_response_structure(response, "test_user1")
        self.assert_cookies_match_response(response)
        self.assert_login_email(
            subject=auth_config.login_alert_email_subject,
            recipient=self.test_user_1.email_address,
        )

    def test_login_with_email_disabled(self):
        """
        Test successful login with email notifications disabled.
        """
        auth_config.email_threading_enabled = False
        auth_config.send_login_alert_emails = False

        response = self.client.post(self.login_url, self.user_1_email_login_data)

        self.assert_response_structure(response, "test_user1")
        self.assert_cookies_match_response(response)
        self.assertEqual(len(mail.outbox), 0)

    def test_user_device_creation(self):
        """
        Test that UserDevice is created after successful login.
        """
        initial_device_count = UserDevice.objects.count()
        response = self.client.post(self.login_url, self.user_1_email_login_data)

        self.assertEqual(UserDevice.objects.count(), initial_device_count + 1)

        # Verify device properties
        device = UserDevice.objects.latest("created_at")
        self.assertEqual(device.account, self.test_user_1)
        self.assertEqual(device.device_id, response.data["device_id"])
        self.assertTrue(device.is_active)

    def test_login_existing_device(self):
        """
        Test login with an existing device ID.
        """
        # First login to create device
        first_response = self.client.post(self.login_url, self.user_1_phone_login_data)
        first_device_id = first_response.data["device_id"]

        # Second login with same credentials
        second_response = self.client.post(self.login_url, self.user_1_phone_login_data)
        second_device_id = second_response.data["device_id"]

        # Verify new device is created
        self.assertNotEqual(first_device_id, second_device_id)

    def test_login_invalid_credentials(self):
        auth_config.email_threading_enabled = False
        """
        Test login with invalid credentials.
        """
        invalid_data = {"login_field": "test_user1", "password": "wrong_password"}
        response = self.client.post(self.login_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(UserDevice.objects.filter(account=self.test_user_1).count(), 0)
        self.assertEqual(len(mail.outbox), 0)

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
            self.assertEqual(
                UserDevice.objects.filter(account=self.test_user_1).count(), 0
            )

    @patch("django.core.mail.send_mail")
    def test_login_email_failure(self, mock_send_mail):
        """
        Test login behavior when email sending fails.
        """
        auth_config.email_threading_enabled = True
        auth_config.send_login_alert_emails = True
        mock_send_mail.side_effect = Exception("Email sending failed")

        response = self.client.post(self.login_url, self.user_1_email_login_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_response_structure(response, "test_user1")

    def test_login_with_email(self):
        """
        Test successful login using email address.
        """
        response = self.client.post(self.login_url, self.user_1_email_login_data)
        self.assert_response_structure(response, "test_user1")
        self.assert_cookies_match_response(response)

        device = UserDevice.objects.latest("created_at")
        self.assertEqual(device.account, self.test_user_1)
        self.assertEqual(device.login_method, "email")

    def test_login_with_phone(self):
        """
        Test successful login using phone number.
        """
        response = self.client.post(self.login_url, self.user_1_phone_login_data)
        self.assert_response_structure(response, "test_user1")
        self.assert_cookies_match_response(response)

        device = UserDevice.objects.latest("created_at")
        self.assertEqual(device.account, self.test_user_1)
        self.assertEqual(device.login_method, "phone")

    def test_login_with_username(self):
        """
        Test successful login using username.
        """
        response = self.client.post(self.login_url, self.user_1_username_login_data)

        self.assert_response_structure(response, "test_user1")
        self.assert_cookies_match_response(response)

        device = UserDevice.objects.latest("created_at")
        self.assertEqual(device.account, self.test_user_1)
        self.assertEqual(device.login_method, "username")
