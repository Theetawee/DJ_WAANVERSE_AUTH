from rest_framework import status

from dj_waanverse_auth.settings import accounts_config

from .test_setup import TestSetup


class TestLoginView(TestSetup):
    def test_mfa_status_not_activated(self):
        accounts_config.AUTH_METHODS = ["phone_number"]
        self.client.post(
            self.login_url,
            {"login_field": self.user.phone_number, "password": "password1"},
            format="json",
        )

        response = self.client.get(self.mfa_status_url)
        self.assertIn("mfa_status", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("recovery_codes", response.data)
        self.assertEqual(response.data["mfa_status"], False)
        self.assertEqual(len(response.data["recovery_codes"]), 0)
