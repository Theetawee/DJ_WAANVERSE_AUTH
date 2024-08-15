from rest_framework import status

from .test_setup import TestSetup


class TestSignUpView(TestSetup):
    def test_signup_view(self):
        response = self.client.post(
            self.signup_url,
            data={
                "username": "user3",
                "password1": "pasSword@3",
                "password2": "pasSword@3",
                "email": "c@c.com",
                "name": "user3",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("msg", response.data)
        self.assertIn("email", response.data)
        self.assertEqual(response.data["msg"], self.messages.status_unverified)

    def test_signup_view_invalid_email(self):
        response = self.client.post(
            self.signup_url,
            data={
                "username": "user3",
                "password1": "pasSword@3",
                "password2": "pasSword@3",
                "email": "testing@invalid",
                "name": "user3",
            },
        )
        self.assertIn("email", response.data)
        self.assertEqual(response.data["email"][0], "Enter a valid email address.")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_already_existing_email(self):
        response = self.client.post(
            self.signup_url,
            data={
                "username": "user3",
                "password1": "pasSword@3",
                "password2": "pasSword@3",
                "email": self.user1.email,
                "name": "user3",
            },
        )
        self.assertIn("email", response.data)
        self.assertEqual(response.data["email"], [self.messages.email_exists])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
