from rest_framework import status

from .test_setup import TestSetup


class TestSignup(TestSetup):
    def test_signup_short_password(self):
        data = {
            "username": "test_user",
            "password": "Test@12",
            "confirm_password": "Test@12",
            "name": "test_user",
        }

        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "This password is too short. It must contain at least 8 characters.",
            response.data["non_field_errors"],
        )

    def test_signup_weak_password(self):
        data = {
            "username": "test_user",
            "password": "Test12",
            "confirm_password": "Test12",
            "name": "test_user",
        }

        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup(self):
        data = {
            "username": "test_user",
            "password": "Test@1220",
            "confirm_password": "Test@1220",
            "name": "test_user",
        }

        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
