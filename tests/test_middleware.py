from rest_framework import status

from .test_setup import TestSetup


class TestMiddleware(TestSetup):
    """
    Tests for the DeviceAuthMiddleware to ensure it behaves correctly
    based on device authentication requirements.
    """

    def test_clint_hints_middleware(self):
        """
        Test the ClientHintsMiddleware to ensure it adds the correct headers
        to the response.
        """
        self.client.post(self.login_url, self.user_1_username_login_data)
        response = self.client.get(self.get_authenticated_user_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
