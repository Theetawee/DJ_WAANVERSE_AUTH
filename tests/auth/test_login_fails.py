from rest_framework import status

from dj_waanverse_auth.settings import accounts_config

from .test_setup import TestSetup


class TestLoginFails(TestSetup):
    def test_login_with_no_login_field(self):
        data = {"email": "a@a.com", "password": "password1"}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.data["login_field"], ["This field is required."])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_no_auth_settings(self):
        accounts_config.AUTH_METHODS = []
        data = {"login_field": "a@a.com", "password": "password1"}
        response = self.client.post(self.login_url, data)
        self.assertEqual(
            response.data["msg"], self.messages.no_account
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_no_user(self):
        accounts_config.AUTH_METHODS = ["email", "username", "phone_number"]
        data = {"login_field": "not_a@a.com", "password": "invalid"}
        response = self.client.post(self.login_url, data)
        self.assertEqual(
            response.data["msg"], self.messages.no_account
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
