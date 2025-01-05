from rest_framework import status

from .test_setup import TestSetup


class TestLogin(TestSetup):
    def test_login(self):
        # Prepare data for the login request
        login_data = {"login_field": "test_user1", "password": "Test@12"}

        response = self.client.post(self.login_url, login_data)

        print(response.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data.get("status"), "success")

        if "access_token" in response.data and "refresh_token" in response.data:
            self.assertTrue("access_token" in response.data)
            self.assertTrue("refresh_token" in response.data)

        if "mfa" in response.data:
            self.assertTrue(isinstance(response.data["mfa"], int))

        if "user" in response.data:
            self.assertTrue("id" in response.data["user"])
            self.assertTrue("email_address" in response.data["user"])
