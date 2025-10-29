from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from dj_waanverse_auth.models import AccessCode
from django.core import mail
from dj_waanverse_auth import settings

Account = get_user_model()


class LoginTests(APITestCase):
    def setUp(self):
        self.login_url = reverse("dj_waanverse_auth_auth")
        self.user = Account.objects.create_user(
            email_address="test@example.com", username="testuser", name="Test User"
        )
        mail.outbox = []

    def test_login_get_code(self):
        response = self.client.post(self.login_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Email address is required.")

        response = self.client.post(
            self.login_url, {"email_address": "test@example.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "Authentication code sent to email.")

        access_code = AccessCode.objects.filter(
            email_address="test@example.com"
        ).first()
        self.assertIsNotNone(access_code)

        self.assertEqual(len(mail.outbox), 1)
        sent_mail = mail.outbox[0]
        self.assertEqual(
            sent_mail.to, ["test@example.com"]
        )
        self.assertIn(access_code.code, sent_mail.body)

    def test_login_verify_code(self):
        response = self.client.post(
            self.login_url, {"email_address": "test@example.com"}
        )
        access_code = AccessCode.objects.filter(
            email_address="test@example.com"
        ).first()

        response = self.client.post(
            self.login_url,
            {"email_address": "test@example.com", "code": access_code.code},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn(settings.access_token_cookie, response.cookies)
        self.assertIn(settings.refresh_token_cookie, response.cookies)
        self.assertIn(settings.access_token_cookie, response.data)
        self.assertIn(settings.refresh_token_cookie, response.data)
        self.assertIn("user", response.data)
        self.assertIn("sid", response.data)
