from django.contrib.auth import get_user_model
from pyotp import TOTP
from rest_framework import status

from dj_waanverse_auth.config.settings import auth_config
from dj_waanverse_auth.models import MultiFactorAuth, UserSession
from dj_waanverse_auth.services.mfa_service import MFAHandler
from dj_waanverse_auth.utils.token_utils import decode_token

from .test_setup import Setup

Account = get_user_model()


class TestMFALogin(Setup):
    def test_get_mfa_secret_view_success(self):
        self.client.post(self.login_url, data=self.user_1_email_login_data)
        response = self.client.post(
            self.get_mfa_secret_view_url,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("secret_key", response.data)
        self.assertIn("provisioning_uri", response.data)
        self.assertTrue(
            MultiFactorAuth.objects.filter(
                account=self.test_user_1, activated=False
            ).exists()
        )

    def test_activate_mfa_success(self):
        self.client.post(self.login_url, data=self.user_1_email_login_data)
        get_mfa_url_response = self.client.post(
            self.get_mfa_secret_view_url,
        )
        secret = get_mfa_url_response.data["secret_key"]
        code = TOTP(secret).now()
        response = self.client.post(
            self.activate_mfa_url,
            {"code": code},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            MultiFactorAuth.objects.filter(
                account=self.test_user_1, activated=True
            ).exists()
        )

    def test_activate_mfa_invalid_code(self):
        self.client.post(self.login_url, data=self.user_1_email_login_data)
        self.client.post(
            self.get_mfa_secret_view_url,
        )
        code = "invalid_code"
        response = self.client.post(
            self.activate_mfa_url,
            {"code": code},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            MultiFactorAuth.objects.filter(
                account=self.test_user_1, activated=True
            ).exists()
        )

    def login_mfa_activated(self):
        response = self.client.post(
            self.login_url, data=self.test_user_with_mfa_login_data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("access_token", response.data)
        self.assertNotIn("refresh_token", response.data)
        self.assertNotIn("user", response.data)
        self.assertIn("mfa", response.data)
        self.assertEqual(response.data["mfa"], self.test_user_with_mfa.id)

    def test_login_mfa_verify(self):
        login_response = self.client.post(
            self.login_url, data=self.test_user_with_mfa_login_data
        )
        last_login = self.test_user_with_mfa.last_login
        user_id = login_response.data["mfa"]
        secret = MFAHandler(user=self.test_user_with_mfa).get_decoded_secret()

        response = self.client.post(
            self.mfa_login_url, {"code": TOTP(secret).now(), "user_id": user_id}
        )
        account = Account.objects.get(id=self.test_user_with_mfa.id)
        self.assertNotEqual(account.last_login, last_login)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn("user", response.data)

        access_token = response.data["access_token"]
        payload = decode_token(access_token)
        session_id = payload["sid"]
        self.assertTrue(UserSession.objects.filter(id=session_id).exists())

    def test_login_mfa_verify_invalid_code(self):
        login_response = self.client.post(
            self.login_url, data=self.test_user_with_mfa_login_data
        )
        user_id = login_response.data["mfa"]
        code = "invalid_code"
        response = self.client.post(
            self.mfa_login_url,
            {"code": code, "user_id": user_id},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("access_token", response.data)
        self.assertNotIn("refresh_token", response.data)
        self.assertNotIn("user", response.data)

    def test_mfa_login_view_recovery_code(self):
        """Handle MFA login using a provided recovery code."""
        mfa_handler = MFAHandler(user=self.test_user_with_mfa)
        mfa_handler.set_recovery_codes()
        self.assertTrue(
            len(mfa_handler.mfa.recovery_codes), auth_config.mfa_recovery_codes_count
        )
        code = mfa_handler.get_recovery_codes()[0]
        login_response = self.client.post(
            self.login_url, data=self.test_user_with_mfa_login_data
        )
        user_id = login_response.data["mfa"]
        response = self.client.post(
            self.mfa_login_url,
            {"code": code, "user_id": user_id},
        )
        self.assertTrue(
            len(mfa_handler.mfa.recovery_codes),
            auth_config.mfa_recovery_codes_count - 1,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn("user", response.data)

    def test_deactivate_mfa_no_password(self):
        login_response = self.client.post(
            self.login_url, data=self.test_user_with_mfa_login_data
        )
        mfa_manager = MFAHandler(user=self.test_user_with_mfa)
        secret = mfa_manager.get_decoded_secret()

        self.client.post(
            self.mfa_login_url,
            {"code": TOTP(secret).now(), "user_id": login_response.data["mfa"]},
        )
        response = self.client.post(
            self.deactivate_mfa_url,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deactivate_mfa_with_password_no_code(self):
        login_response = self.client.post(
            self.login_url, data=self.test_user_with_mfa_login_data
        )
        mfa_manager = MFAHandler(user=self.test_user_with_mfa)
        secret = mfa_manager.get_decoded_secret()

        self.client.post(
            self.mfa_login_url,
            {"code": TOTP(secret).now(), "user_id": login_response.data["mfa"]},
        )
        response = self.client.post(
            self.deactivate_mfa_url,
            {"password": self.test_user_with_mfa_login_data["password"]},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deactivate_mfa_with_password_and_code(self):
        login_response = self.client.post(
            self.login_url, data=self.test_user_with_mfa_login_data
        )
        mfa_manager = MFAHandler(user=self.test_user_with_mfa)
        secret = mfa_manager.get_decoded_secret()

        self.client.post(
            self.mfa_login_url,
            {"code": TOTP(secret).now(), "user_id": login_response.data["mfa"]},
        )
        response = self.client.post(
            self.deactivate_mfa_url,
            {
                "password": self.test_user_with_mfa_login_data["password"],
                "code": TOTP(secret).now(),
            },
        )
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            MultiFactorAuth.objects.filter(
                account=self.test_user_with_mfa, activated=True
            ).exists()
        )

    def test_deactivate_mfa_with_password_and_invalid_code(self):
        login_response = self.client.post(
            self.login_url, data=self.test_user_with_mfa_login_data
        )
        mfa_manager = MFAHandler(user=self.test_user_with_mfa)
        secret = mfa_manager.get_decoded_secret()

        self.client.post(
            self.mfa_login_url,
            {"code": TOTP(secret).now(), "user_id": login_response.data["mfa"]},
        )
        response = self.client.post(
            self.deactivate_mfa_url,
            {
                "password": self.test_user_with_mfa_login_data["password"],
                "code": "invalid_code",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            MultiFactorAuth.objects.filter(
                account=self.test_user_with_mfa, activated=True
            ).exists()
        )

    def test_generate_recovery_codes(self):
        login_response = self.client.post(
            self.login_url, data=self.test_user_with_mfa_login_data
        )
        mfa_manager = MFAHandler(user=self.test_user_with_mfa)
        secret = mfa_manager.get_decoded_secret()

        self.client.post(
            self.mfa_login_url,
            {"code": TOTP(secret).now(), "user_id": login_response.data["mfa"]},
        )

        response = self.client.post(
            self.generate_mfa_recovery_codes_url,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            MultiFactorAuth.objects.filter(
                account=self.test_user_with_mfa, activated=True
            ).exists()
        )
        self.assertTrue(
            len(
                MultiFactorAuth.objects.filter(account=self.test_user_with_mfa)
                .first()
                .recovery_codes
            ),
            auth_config.mfa_recovery_codes_count,
        )

    def test_get_recovery_codes_no_codes(self):
        login_response = self.client.post(
            self.login_url, data=self.test_user_with_mfa_login_data
        )
        user_id = login_response.data["mfa"]
        mfa_manager = MFAHandler(user=self.test_user_with_mfa)
        secret = mfa_manager.get_decoded_secret()

        self.client.post(
            self.mfa_login_url, {"code": TOTP(secret).now(), "user_id": user_id}
        )

        response = self.client.get(
            self.get_recovery_codes_url,
        )
        self.assertEqual(response.data["msg"], "no_codes")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_recovery_codes(self):
        login_response = self.client.post(
            self.login_url, data=self.test_user_with_mfa_login_data
        )
        mfa_manager = MFAHandler(user=self.test_user_with_mfa)
        secret = mfa_manager.get_decoded_secret()
        mfa_manager.set_recovery_codes()
        self.client.post(
            self.mfa_login_url,
            {"code": TOTP(secret).now(), "user_id": login_response.data["mfa"]},
        )

        response = self.client.get(
            self.get_recovery_codes_url,
        )
        self.assertIn("recovery_codes", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
