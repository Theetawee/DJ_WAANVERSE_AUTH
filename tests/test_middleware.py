from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from dj_waanverse_auth.settings import auth_config

from .test_setup import TestSetup


class TestMiddleware(TestSetup):
    """
    Tests for the DeviceAuthMiddleware to ensure it behaves correctly
    based on device authentication requirements.
    """

    def test_middleware_blocked_access(self):
        """
        Ensure that access to a protected endpoint is blocked without a valid device ID.
        """
        response = self.client.get(self.home_page_url)
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_middleware_allowed_access_through_cookie(self):
        """
        Test that the middleware allows access when a valid device ID is provided in a cookie.
        """
        self.client.post(self.login_url, data=self.user_1_email_login_data)

        response = self.client.get(self.home_page_url)
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_middleware_allowed_access_through_header(self):
        """
        Test that the middleware allows access when a valid device ID is provided in headers.
        """
        login_response = self.client.post(
            self.login_url, data=self.user_1_phone_login_data
        )

        device_id = login_response.data.get("device_id")
        self.assertIsNotNone(device_id)

        # Add the device ID to headers for authentication
        self.client.defaults["HTTP_" + auth_config.device_id_header_name.upper()] = (
            device_id
        )

        # Remove cookie to simulate header-based authentication
        self.client.cookies.pop(auth_config.device_id_cookie_name, None)

        # Confirm the cookie was removed
        self.assertNotIn(auth_config.device_id_cookie_name, self.client.cookies)

        response = self.client.get(self.home_page_url)
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_middleware_excluded_path(self):
        """
        Ensure that middleware does not enforce device authentication for excluded paths.
        """
        auth_config.device_auth_excluded_paths.append(self.home_page_url)
        response = self.client.get(self.home_page_url)
        self.assertEqual(response.status_code, HTTP_200_OK)
