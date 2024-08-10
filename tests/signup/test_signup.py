from .test_setup import TestSetup
from rest_framework import status


class TestSignupViews(TestSetup):

    def test_signup_bad_password(self):

        data = {
            "username": "testuser1",
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpassword",
            "date_of_birth": "1990-01-01",
            "phone_number": "1234567890",
            "password1": "testpassword",
            "password2": "badpassword",
        }

        response = self.client.post(self.signup_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup(self):

        data = {
            "username": "testuser1",
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpassword",
            "date_of_birth": "1990-01-01",
            "phone_number": "1234567890",
            "password1": "testpassword1",
            "password2": "testpassword",
        }

        response = self.client.post(self.signup_url, data)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
