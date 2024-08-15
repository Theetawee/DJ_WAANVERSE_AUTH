from rest_framework import status

from dj_waanverse_auth.models import ResetPasswordCode

from .test_setup import TestSetup


class TestResetPassword(TestSetup):
    def test_reset_password_view(self):
        response = self.client.post(
            self.reset_password_url, {"email": self.user1.email}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("msg", response.data)
        self.assertIn("attempts", response.data)
        self.assertEqual(
            response.data["msg"], self.messages.password_reset_code_sent
        )

        self.assertEqual(response.data["email"], self.user1.email)
        self.assertIn("email", response.data)

        base = ResetPasswordCode.objects.get(email=self.user1.email)

        res = self.client.post(
            self.verify_rest_password_url,
            {
                "code": base.code,
                "new_password1": "passWord#3",
                "new_password2": "passWord#3",
                "email": self.user1.email,
            },
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("msg", res.data)
        self.assertEqual(res.data["msg"], self.messages.password_reset_successful)

    def test_reset_password_view_invalid_email(self):
        response = self.client.post(
            self.reset_password_url, {"email": "testing@invalid.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rest_password_view_invalid_code(self):
        response = self.client.post(
            self.verify_rest_password_url,
            {
                "code": "invalid",
                "new_password1": "passWord#3",
                "new_password2": "passWord#3",
                "email": self.user1.email,
            },
        )
        self.assertEqual(response.data["msg"], [self.messages.invalid_code])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_view_invalid_password(self):
        self.client.post(self.reset_password_url, {"email": self.user1.email})
        base = ResetPasswordCode.objects.get(email=self.user1.email)

        response = self.client.post(
            self.verify_rest_password_url,
            {
                "code": base.code,
                "new_password1": "passWord#3",
                "new_password2": "passWord#4",
                "email": self.user1.email,
            },
        )
        self.assertEqual(
            response.data["msg"], [self.messages.password_mismatch]
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
