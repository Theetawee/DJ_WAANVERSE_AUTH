from rest_framework import status

from dj_waanverse_auth.settings import auth_config

from .test_setup import TestSetup


class TestLogin(TestSetup):
    def setUp(self):
        super().setUp()
        self.login_data = {"login_field": "test_user1", "password": "Test@12"}

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

    def assert_response_structure(self, response):
        """
        Helper function to assert response structure and content.
        """
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("status"), "success")

        required_fields = ["access_token", "refresh_token", "user", "device_id"]
        for field in required_fields:
            self.assertIn(field, response.data, f"Missing field: {field}")

        user_data = response.data["user"]
        self.assertEqual(user_data["username"], "test_user1")
        self.assertIn("id", user_data)
        self.assertIn("email_address", user_data)

    def assert_cookies_match_response(self, response):
        """
        Helper function to assert cookies match response data.
        """
        # Get cookies
        cookies = {
            "refresh": self.client.cookies.get(auth_config.refresh_token_cookie),
            "access": self.client.cookies.get(auth_config.access_token_cookie),
            "device": self.client.cookies.get(auth_config.device_id_cookie_name),
        }

        # Check if all cookies exist
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

    def test_login_not_mfa(self):
        """
        Test successful login without MFA.
        """
        # Perform login
        response = self.client.post(self.login_url, self.login_data)

        self.assert_response_structure(response)

        # Assert cookies match response data
        self.assert_cookies_match_response(response)

    def test_login_invalid_credentials(self):
        """
        Test login with invalid credentials.
        """
        invalid_data = {"login_field": "test_user1", "password": "wrong_password"}
        response = self.client.post(self.login_url, invalid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_fields(self):
        """
        Test login with missing required fields.
        """
        incomplete_data = {"login_field": "test_user1"}
        response = self.client.post(self.login_url, incomplete_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
