from django.urls import reverse
from django.core import mail
from django.contrib.auth import get_user_model
from rest_framework import status
from dj_waanverse_auth.models import AccessCode
from dj_waanverse_auth import settings as auth_config
from tests.base import BaseAPITestCase
from django.utils import timezone
from datetime import timedelta

Account = get_user_model()


class LoginCodeRequestTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("dj_waanverse_auth_login")
        self.email = "newuser@example.com"
        self.account = Account.objects.create_user(
            email_address=self.email,
        )

    def test_login_code_request(self):
        response = self.client.post(self.url, {"email_address": self.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, auth_config.login_code_email_subject)
        self.assertEqual(mail.outbox[0].to, [self.email])

        access_code = AccessCode.objects.get(email_address=self.email)
        self.assertEqual(access_code.email_address, self.email)

    def test_login_code_request_with_none_email(self):
        response = self.client.post(self.url, {"email_address": None})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_code_request_with_invalid_email(self):
        response = self.client.post(self.url, {"email_address": "invalid_email"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LoginCodeVerifyTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("dj_waanverse_auth_login")
        self.email = "newuser@example.com"
        self.account = Account.objects.create_user(
            email_address=self.email,
            last_login=timezone.now() - timedelta(minutes=5),
        )
        AccessCode.objects.create(
            email_address=self.email,
            code="123456",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

    def test_login_code_verify(self):
        first_login_time = self.account.last_login
        response = self.client.post(
            self.url, {"email_address": self.email, "code": "123456"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLoginData(response)
        self.assertAuthCookies(response)
        self.account.refresh_from_db()
        self.assertNotEqual(
            first_login_time,
            Account.objects.filter(email_address=self.email).first().last_login,
        )
