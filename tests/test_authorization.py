from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from dj_waanverse_auth.models import UserSession
from dj_waanverse_auth.models import LoginCode
from django.utils import timezone
from datetime import timedelta
from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.utils.token_utils import decode_token, encode_token

User = get_user_model()


class AuthViewsTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email_address="test@example.com", email_verified=True, is_active=True
        )

        # Create an authenticated session
        self.session = UserSession.objects.create(account=self.user)
        # URLs
        self.refresh_access_token_url = reverse(
            "dj_waanverse_auth_refresh_access_token"
        )
        self.get_authenticated_user_url = reverse(
            "dj_waanverse_auth_authenticated_user"
        )
        self.logout_url = reverse("dj_waanverse_auth_logout")
        self.sessions_url = reverse("dj_waanverse_auth_get_user_sessions")
        self.delete_session_url = reverse(
            "dj_waanverse_auth_delete_user_session",
            kwargs={"session_id": self.session.id},
        )

    def log_user_in(self):
        self.url = reverse("dj_waanverse_auth_login")
        LoginCode.objects.create(
            account=self.user,
            code="123456",
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        response = self.client.post(
            self.url, {"email_address": "test@example.com", "code": "123456"}
        )

        return response

    def test_refresh_access_token_use_cookie(self):
        self.log_user_in()

        response = self.client.post(
            self.refresh_access_token_url,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)

    def test_refresh_access_token_use_token(self):
        login_response = self.log_user_in()
        refresh_token = login_response.data["refresh_token"]

        # remove cookie
        self.client.cookies.pop(
            auth_config.refresh_token_cookie,
        )

        response = self.client.post(
            self.refresh_access_token_url,
            data={"refresh_token": refresh_token},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)

    def test_refresh_access_token_no_token(self):
        self.log_user_in()

        # remove cookie
        self.client.cookies.pop(
            auth_config.refresh_token_cookie,
        )

        response = self.client.post(
            self.refresh_access_token_url,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_authenticated_user_with_bearer_token(self):
        login_response = self.log_user_in()

        access_token = login_response.data["access_token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # remove cookie
        self.client.cookies.pop(
            auth_config.access_token_cookie,
        )

        self.assertNotIn(auth_config.access_token_cookie, self.client.cookies)

        response = self.client.get(self.get_authenticated_user_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email_address"], self.user.email_address)

    def test_access_with_invalid_sid(self):
        login_response = self.log_user_in()
        access_token = login_response.data["access_token"]
        payload = decode_token(access_token)
        payload["sid"] = "invalid"
        access_token = encode_token(payload)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        response = self.client.get(self.get_authenticated_user_url)
        self.assertIn("identity_error", response.data["detail"])
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_with_invalid_user_id(self):
        login_response = self.log_user_in()

        access_token = login_response.data["access_token"]
        payload = decode_token(access_token)
        payload["id"] = "0"
        access_token = encode_token(payload)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        response = self.client.get(self.get_authenticated_user_url)
        self.assertIn("user_not_found", response.data["detail"])
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_jwt_claims(self):
        response = self.log_user_in()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data.get("access_token")
        self.assertIsNotNone(access_token)

        payload = decode_token(access_token)
        payload.pop("sid", None)  # Remove "sid" claim
        tampered_token = encode_token(payload)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered_token}")
        new_response = self.client.get(self.get_authenticated_user_url)
        self.assertEqual(new_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid token structure", new_response.data["detail"])

    def test_tampered_token_signature(self):
        response = self.log_user_in()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data.get("access_token")
        self.assertIsNotNone(access_token)

        tampered_token = access_token[:-1] + (
            "ark" if access_token[-1] != "milk" else "bag of water"
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered_token}")
        new_response = self.client.get(self.get_authenticated_user_url)
        self.assertEqual(new_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid token structure", new_response.data["detail"])

    def test_logout(self):
        login_response = self.log_user_in()
        access_token = login_response.data["access_token"]
        payload = decode_token(access_token)
        session_id = payload["sid"]
        self.assertTrue(UserSession.objects.filter(id=session_id).exists())
        self.assertTrue(UserSession.objects.get(id=session_id).is_active)
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for cookie_name in response.cookies:
            self.assertEqual(
                response.cookies[cookie_name].value,
                "",
                f"Cookie {cookie_name} was not removed",
            )

        self.assertFalse(UserSession.objects.filter(id=session_id).exists())
