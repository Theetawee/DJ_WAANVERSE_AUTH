from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from django.urls import reverse
from dj_waanverse_auth.models import AccessCode, UserSession
from django.utils import timezone

Account = get_user_model()


class AuthTests(APITestCase):
    def setUp(self):
        self.auth_url = reverse("dj_waanverse_auth_me")
        self.login_url = reverse("dj_waanverse_auth_auth")
        self.user = Account.objects.create_user(
            email_address="test@example.com", username="testuser", name="Test User"
        )

    def test_authenticated_user_unauthenticated(self):
        """Unauthenticated request to /me/ should be rejected."""
        response = self.client.get(self.auth_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"], "Authentication credentials were not provided."
        )

    def test_authenticated_user_authenticated(self):
        """Authenticated request to /me/ should return user details."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.auth_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email_address"], "test@example.com")

    def test_logout_user(self):
        """User can log out successfully."""
        AccessCode.objects.create(
            email_address="test@example.com",
            code="123456",
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        response = self.client.post(
            self.login_url, {"email_address": "test@example.com", "code": "123456"}
        )

        sid = response.data.get("sid")

        response = self.client.post(
            reverse("dj_waanverse_auth_logout", kwargs={"session_id": sid})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertFalse(UserSession.objects.filter(id=sid).exists())

        resp = self.client.get(self.auth_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
