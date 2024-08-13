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
        self.assertIn("status", response.data)
        self.assertIn("email", response.data)
        self.assertEqual(response.data["status"], "unverified")
