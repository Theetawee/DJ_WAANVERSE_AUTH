from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from tests.base import BaseAPITestCase
from dj_waanverse_auth.models import AccessCode
from django.utils import timezone
from datetime import timedelta
from dj_waanverse_auth import settings as auth_settings
from dj_waanverse_auth.utils.token_utils import decode_token, encode_token
from dj_waanverse_auth.models import UserSession

Account = get_user_model()


class AuthenticationTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.email = "test_user@gmail.com"
        self.email2 = "test2@gmail.com"
        AccessCode.objects.create(
            email_address=self.email,
            code="123456",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        AccessCode.objects.create(
            email_address=self.email2,
            code="123457",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        self.me_url = reverse("dj_waanverse_auth_me")
        self.login_url = reverse("dj_waanverse_auth_login")
        self.refresh_url = reverse("dj_waanverse_auth_refresh_token")
        self.sessions_url = reverse("dj_waanverse_auth_sessions")
        self.account = Account.objects.create_user(email_address=self.email)
        self.account2 = Account.objects.create_user(email_address=self.email2)

        self.client.force_authenticate(self.account)

    def test_get_user_info_unauthenticated(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_logged_in_user_info(self):
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.email, response.data["email_address"])

    def test_get_logged_in_user_info_using_header(self):

        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.login_url,
            {"email_address": self.email2, "code": "123457"},
        )

        access_token = response.cookies[auth_settings.access_token_cookie].value

        self.client.cookies.clear()

        response = self.client.get(
            self.sessions_url,
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        self.assertEqual(response.data[0]["account"], self.account2.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_logged_in_user_info_altered_key(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.login_url,
            {"email_address": self.email2, "code": "123457"},
        )

        access_token = response.cookies[auth_settings.access_token_cookie].value

        payload = decode_token(access_token)

        payload["sid"] = 0

        new_token = encode_token(payload)

        self.client.cookies.clear()

        resp = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION=f"Bearer {new_token}",
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("identity_error", resp.data["detail"])

    def test_refresh_token_using_cookie(self):
        self.client.post(
            self.login_url, {"email_address": self.email, "code": "123456"}
        )

        new_resp = self.client.post(self.refresh_url)

        self.assertTrue(new_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(new_resp.data["message"], "Token refreshed successfully")

    def test_refresh_token_using_token(self):
        # First login
        response = self.client.post(
            self.login_url,
            {"email_address": self.email, "code": "123456"},
        )

        refresh_cookie_name = auth_settings.refresh_token_cookie

        # Extract the token value (not the cookie object)
        refresh_token = response.cookies[refresh_cookie_name].value

        # Clear all cookies from the test client
        self.client.cookies.clear()

        # Now call refresh using only the token in body
        new_resp = self.client.post(
            self.refresh_url,
            {"refresh_token": refresh_token},
        )

        self.assertEqual(new_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(new_resp.data["message"], "Token refreshed successfully")

    def test_refresh_token_using_token_blank_or_altered(self):
        # First login
        response = self.client.post(
            self.login_url,
            {"email_address": self.email, "code": "123456"},
        )

        refresh_cookie_name = auth_settings.refresh_token_cookie

        # Extract the token value (not the cookie object)
        refresh_token = response.cookies[refresh_cookie_name].value

        # Clear all cookies from the test client
        self.client.cookies.clear()

        # Now call refresh using only the token in body
        new_resp = self.client.post(
            self.refresh_url,
        )

        access_cookie_value = new_resp.cookies[auth_settings.access_token_cookie]
        refresh_cookie_value = new_resp.cookies[auth_settings.refresh_token_cookie]

        self.assertEqual(access_cookie_value.value, "")
        self.assertEqual(refresh_cookie_value.value, "")

        self.assertEqual(new_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(new_resp.data["error"], "Refresh token is required.")

        payload = decode_token(refresh_token)

        payload["sid"] = 0

        new_token = encode_token(payload)

        new_resp2 = self.client.post(
            self.refresh_url,
            {"refresh_token": new_token},
        )

        self.assertEqual(len(new_resp2.cookies), 0)
        self.assertEqual(new_resp2.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(new_resp2.data["error"], "Invalid refresh token.")

    def test_token_claims(self):
        response = self.client.post(
            self.login_url,
            {"email_address": self.email2, "code": "123457"},
        )

        refresh_cookie_name = auth_settings.refresh_token_cookie
        access_cookie_name = auth_settings.access_token_cookie

        # Extract the token value (not the cookie object)
        refresh_token = response.cookies[refresh_cookie_name].value
        access_token = response.cookies[access_cookie_name].value

        refresh_payload = decode_token(refresh_token)
        access_payload = decode_token(access_token)

        session = UserSession.objects.filter(account=self.account2).first()

        self.assertEqual(refresh_payload["id"], self.account2.id)
        self.assertEqual(refresh_payload["token_type"], "refresh")
        self.assertEqual(refresh_payload["sid"], session.id)
        self.assertEqual(refresh_payload["iss"], auth_settings.platform_name)

        self.assertEqual(access_payload["token_type"], "access")

    def test_refresh_token_invalid_session(self):
        response = self.client.post(
            self.login_url,
            {"email_address": self.email2, "code": "123457"},
        )

        refresh_cookie_name = auth_settings.refresh_token_cookie

        # Extract the token value (not the cookie object)
        refresh_token = response.cookies[refresh_cookie_name].value

        payload = decode_token(refresh_token)
        UserSession.objects.get(id=payload["sid"]).delete()

        self.assertFalse(UserSession.objects.filter(id=payload["sid"]).exists())

        new_resp = self.client.post(self.refresh_url)

        self.assertEqual(new_resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout(self):
        response = self.client.post(
            self.login_url,
            {"email_address": self.email2, "code": "123457"},
        )

        sid = response.data["sid"]
        self.assertTrue(UserSession.objects.filter(id=sid).exists())

        self.logout_url = reverse("dj_waanverse_auth_logout", args=[sid])

        new_resp = self.client.post(self.logout_url)

        self.assertEqual(new_resp.status_code, status.HTTP_200_OK)
        self.assertFalse(UserSession.objects.filter(id=sid).exists())

    def test_delete_session(self):
        response = self.client.post(
            self.login_url,
            {"email_address": self.email2, "code": "123457"},
        )

        sid = response.data["sid"]
        self.assertTrue(UserSession.objects.filter(id=sid).exists())

        self.delete_url = reverse("dj_waanverse_auth_delete_session", args=[sid])

        new_resp = self.client.delete(self.delete_url)

        self.assertEqual(new_resp.status_code, status.HTTP_200_OK)
        self.assertFalse(UserSession.objects.filter(id=sid).exists())

        self.delete_url = reverse("dj_waanverse_auth_delete_session", args=[0])

        new_resp = self.client.delete(self.delete_url)

        self.assertEqual(new_resp.status_code, status.HTTP_404_NOT_FOUND)
