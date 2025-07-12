from django.test import override_settings
from rest_framework import status
from django.urls import reverse
from .test_setup import Setup


class TestMiddleware(Setup):
    """
    Tests for the DeviceAuthMiddleware to ensure it behaves correctly
    based on device authentication requirements.
    """

    def setUp(self):
        super().setUp()
        self.url = reverse("dj_waanverse_auth_get_device_info")

    def test_clint_hints_middleware(self):
        """
        Test the ClientHintsMiddleware to ensure it adds the correct headers
        to the response.
        """
        self.client.post(self.login_url, self.user_1_username_login_data)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(
    BLOCKED_IPS=["192.168.1.100"],
    ALLOWED_IPS=["8.8.8.8"],
)
class TestIPBlockMiddleware(Setup):
    """
    Tests for the IPBlockerMiddleware to ensure it behaves correctly
    based on IP blocking requirements.
    """

    def setUp(self):
        super().setUp()
        self.url = reverse("dj_waanverse_auth_signup")

    def test_ip_block_middleware(self):
        """
        Test the IPBlockerMiddleware to ensure it blocks the correct IP addresses
        and allows the correct IP addresses.
        """
        self.client.post(self.login_url, self.user_1_username_login_data)
        # Test blocked IP
        response = self.client.get(
            self.get_authenticated_user_url, REMOTE_ADDR="192.168.1.100"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Access denied", response.data["detail"])

        # Test allowed IP
        response = self.client.get(
            self.get_authenticated_user_url, REMOTE_ADDR="8.8.8.8"
        )
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
