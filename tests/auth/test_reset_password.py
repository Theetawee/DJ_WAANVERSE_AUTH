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
            response.data["msg"], "Password reset code has been sent successfully."
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
        self.assertEqual(res.data["msg"], "Password has been reset successfully.")
