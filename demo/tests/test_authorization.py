from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from dj_waanverse_auth.models import UserSession
from dj_waanverse_auth.models import LoginCode
from django.utils import timezone
from datetime import timedelta
from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.utils.token_utils import decode_token, encode_token
from django.utils import timezone

User = get_user_model()


class AuthViewsTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email_address="test@example.com", email_verified=True, is_active=True
        )

        # Create an authenticated session
        self.client.force_authenticate(user=self.user)
        self.session = UserSession.objects.create(account=self.user)
        # URLs
        self.refresh_url = reverse("dj_waanverse_auth_refresh_access_token")
        self.auth_user_url = reverse("dj_waanverse_auth_authenticated_user")
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

    def test_access_denied_expired_access_token(self):
        # Log the user in and get the valid token
        response = self.log_user_in()
        access_token = response.cookies.get(auth_config.access_token_cookie)

        # Decode existing token
        payload = decode_token(access_token.value)

        print(payload)

        # Set expiration to 1 minute in the past
        payload["exp"] = int(
            (
                auth_config.access_token_cookie_max_age.total_seconds()
                + timedelta(hours=1).total_seconds()
            )
        )

        # Encode the new "expired" token
        expired_token = encode_token(payload)

        # Replace cookie with expired one
        self.client.cookies[auth_config.access_token_cookie] = expired_token

        # Try accessing a protected route
        res = self.client.get(self.auth_user_url)

        # Expect unauthorized due to expiration
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    # def test_refresh_access_token_success_using_refresh_cookie(self):

    #     res = self.client.post(self.refresh_url, {"refresh_token": "valid_token"})
    #     self.assertEqual(res.status_code, status.HTTP_200_OK)
    #     self.assertIn("access_token", res.data)

    # def test_refresh_access_token_missing_token(self):
    #     self.client.logout()
    #     res = self.client.post(self.refresh_url, {})
    #     self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # @patch("dj_waanverse_auth.views.authorization_views.TokenService.verify_token")
    # def test_refresh_access_token_invalid_token(self, mock_verify):
    #     mock_verify.return_value = False
    #     self.client.logout()
    #     res = self.client.post(self.refresh_url, {"refresh_token": "bad"})
    #     self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    # def test_authenticated_user_returns_data(self):
    #     res = self.client.get(self.auth_user_url)
    #     self.assertEqual(res.status_code, status.HTTP_200_OK)
    #     self.assertEqual(res.data["id"], self.user.id)

    # @patch("dj_waanverse_auth.views.authorization_views.decode_token")
    # def test_logout_view_success(self, mock_decode):
    #     mock_decode.return_value = {"sid": str(self.session.id)}
    #     res = self.client.post(self.logout_url, {"access_token": "dummy"})
    #     self.assertEqual(res.status_code, status.HTTP_200_OK)
    #     self.assertEqual(res.data["status"], "success")

    # def test_logout_view_missing_access_token(self):
    #     res = self.client.post(self.logout_url, {})
    #     self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # @patch("dj_waanverse_auth.views.authorization_views.decode_token")
    # def test_logout_view_missing_session_id(self, mock_decode):
    #     mock_decode.return_value = {}
    #     res = self.client.post(self.logout_url, {"access_token": "dummy"})
    #     self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # @patch("dj_waanverse_auth.views.authorization_views.decode_token")
    # def test_logout_view_session_not_found(self, mock_decode):
    #     mock_decode.return_value = {"sid": "99999"}
    #     res = self.client.post(self.logout_url, {"access_token": "dummy"})
    #     self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # def test_get_user_sessions(self):
    #     res = self.client.get(self.sessions_url)
    #     self.assertEqual(res.status_code, status.HTTP_200_OK)
    #     self.assertIsInstance(res.data, list)

    # def test_delete_user_session_success(self):
    #     self.client.logout()  # endpoint allows any
    #     res = self.client.delete(self.delete_session_url)
    #     self.assertEqual(res.status_code, status.HTTP_200_OK)

    # def test_delete_user_session_not_found(self):
    #     url = reverse("delete_user_session", kwargs={"session_id": 99999})
    #     self.client.logout()
    #     res = self.client.delete(url)
    #     self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
