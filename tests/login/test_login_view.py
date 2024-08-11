from dj_waanverse_auth.settings import accounts_config

from .test_setup import TestSetup


class TestLoginView(TestSetup):
    def test_login_view_non_verified(self):
        accounts_config.AUTH_METHODS = ["username"]

        user_data = {
            "login_field": self.user1.username,
            "password": "password1",
        }
        response = self.client.post(self.login_url, user_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.data)
        self.assertIn("status", response.data)
        self.assertEqual(response.data["status"], "unverified")
        self.assertEqual(response.data["email"], self.user1.email)

    def test_login_view_verified_email(self):
        accounts_config.AUTH_METHODS = ["email"]
        user_data = {
            "login_field": self.user2.email,
            "password": "password2",
        }
        response = self.client.post(self.login_url, user_data, format="json")
        self.assert_auth_cookies(response)
        self.assert_auth_response(response)

    def test_login_view_verified_phone_number(self):
        accounts_config.AUTH_METHODS = ["phone_number"]
        user_data = {
            "login_field": self.user1.phone_number,
            "password": "password1",
        }
        response = self.client.post(self.login_url, user_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.data)
        self.assertIn("status", response.data)
        self.assertEqual(response.data["status"], "unverified")
        self.assertEqual(response.data["email"], self.user1.email)
