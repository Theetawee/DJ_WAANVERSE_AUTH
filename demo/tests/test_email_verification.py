from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core import mail
from dj_waanverse_auth.models import VerificationCode
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

Account = get_user_model()


class TestEmailVerificationViews(APITestCase):
    def setUp(self):
        mail.outbox = []
        self.user_unverified = Account.objects.create_user(
            email_address="test_unverified@gmail.com",
            email_verified=False,
            is_active=False,
        )
        self.user_verified = Account.objects.create_user(
            email_address="test_verified@gmail.com", email_verified=True, is_active=True
        )
        self.send_url = reverse("dj_waanverse_auth_send_email_verification_code")
        self.activate_url = reverse("dj_waanverse_auth_activate_email")

    def test_activate_email_success(self):
        VerificationCode.objects.create(
            email_address=self.user_unverified.email_address,
            code="123456",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        data = {
            "email_address": self.user_unverified.email_address,
            "code": "123456",
            "handle": "signup",
        }
        response = self.client.post(self.activate_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user_unverified.refresh_from_db()
        self.assertTrue(self.user_unverified.email_verified)
        self.assertTrue(self.user_unverified.is_active)
        self.assertFalse(
            VerificationCode.objects.filter(
                email_address=self.user_unverified.email_address
            ).exists()
        )
        for key in ["user", "access_token", "refresh_token", "sid"]:
            self.assertIn(key, response.data)

    def test_activate_email_expired_code(self):
        VerificationCode.objects.create(
            email_address=self.user_unverified.email_address,
            code="123456",
            expires_at=timezone.now() - timedelta(minutes=1),  # already expired
        )
        data = {
            "email_address": self.user_unverified.email_address,
            "code": "123456",
            "handle": "signup",
        }
        response = self.client.post(self.activate_url, data)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code_expired", str(response.data))
        self.assertFalse(
            VerificationCode.objects.filter(
                email_address=self.user_unverified.email_address
            ).exists()
        )
