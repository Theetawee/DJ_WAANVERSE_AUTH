from rest_framework import status

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
            print(response.data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
