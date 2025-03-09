from rest_framework import status

from dj_waanverse_auth import settings

from .setup import Setup


class TestSignupView(Setup):

    def test_signup_view(self):
        data = {
            "username": {
                "username": "test_user",
                "password": "Test@1220",
                "confirm_password": "Test@1220",
            },
            "email": {
                "email_address": "9Vz2K@example.com",
                "password": "Test@1220",
                "confirm_password": "Test@1220",
            },
            "phone_number": {
                "phone_number": "1234567890",
                "password": "Test@1220",
                "confirm_password": "Test@1220",
            },
        }

        for key, value in data.items():
            response = self.client.post(self.signup_url, value)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            expected_cookies = [
                settings.access_token_cookie,
                settings.refresh_token_cookie,
            ]
            expected_response_data = ["status", "access_token", "refresh_token"]
            for cookie_name in expected_cookies:
                self.assertIn(cookie_name, response.cookies)

            for field in expected_response_data:
                self.assertIn(field, response.data)
