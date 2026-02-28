from django.urls import reverse
from django.core import mail
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from datetime import timedelta

from dj_waanverse_auth.models import AccessCode
from dj_waanverse_auth import settings as auth_config
from tests.base import BaseAPITestCase

Account = get_user_model()


# =========================
# SIGNUP CODE REQUEST TESTS
# =========================


class SignupCodeRequestTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse("dj_waanverse_auth_signup")
        self.email = "newuser@example.com"
        auth_config.disable_signup = False

    def test_signup_requires_email(self):
        response = self.client.post(self.url, {})
        self.assertErrorResponse(response)
        self.assertEqual(response.data["detail"], "Email address is required.")

    def test_signup_rejects_invalid_email(self):
        response = self.client.post(self.url, {"email_address": "invalid"})
        self.assertErrorResponse(response)
        self.assertEqual(response.data["detail"], "Invalid email address format.")

    def test_signup_rejects_blacklisted_email(self):
        auth_config.blacklisted_emails = ["blocked@gmail.com"]

        response = self.client.post(self.url, {"email_address": "blocked@gmail.com"})

        self.assertErrorResponse(response)
        self.assertEqual(
            response.data["detail"], "This email address is blocked from registration."
        )

    def test_signup_rejects_blacklisted_domain(self):
        auth_config.blacklisted_email_domains = ["blocked.com"]

        response = self.client.post(self.url, {"email_address": "user@blocked.com"})

        self.assertErrorResponse(response)
        self.assertEqual(
            response.data["detail"], "This email domain is blocked from registration."
        )

    def test_signup_rejects_invalid_allowed_domain(self):
        auth_config.allowed_email_domains = ["gmail.com"]

        response = self.client.post(self.url, {"email_address": "user@yahoo.com"})

        self.assertErrorResponse(response)
        self.assertEqual(response.data["detail"], "Invalid email domain.")

    def test_signup_rejects_existing_account(self):
        Account.objects.create(email_address=self.email)

        response = self.client.post(self.url, {"email_address": self.email})

        self.assertErrorResponse(response)
        self.assertEqual(response.data["detail"], "Account already exists.")

    def test_signup_rate_limited(self):
        self.client.post(self.url, {"email_address": self.email})
        response = self.client.post(self.url, {"email_address": self.email})

        self.assertErrorResponse(response)
        self.assertIn("Please wait", response.data["detail"])

    def test_signup_disabled(self):
        auth_config.disable_signup = True

        response = self.client.post(self.url, {"email_address": self.email})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "Pong")
        self.assertFalse(AccessCode.objects.filter(email_address=self.email).exists())

    def test_signup_testing_email(self):
        testing_email = "test@example.com"
        auth_config.testing_email_addresses = [testing_email]
        auth_config.is_testing = True

        response = self.client.post(self.url, {"email_address": testing_email})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            AccessCode.objects.filter(email_address=testing_email).exists()
        )

    def test_signup_code_sent_successfully(self):
        response = self.client.post(self.url, {"email_address": self.email})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "Signup code sent to email.")

        self.assertFalse(Account.objects.filter(email_address=self.email).exists())

        self.assertTrue(AccessCode.objects.filter(email_address=self.email).exists())

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.email, mail.outbox[0].to)


# ==========================
# SIGNUP CODE VALIDATION TESTS
# ==========================


class SignupCodeValidationTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse("dj_waanverse_auth_signup")
        self.email = "newuser@example.com"
        auth_config.disable_signup = False

    def _create_code(self, expires_delta_minutes=5):
        return AccessCode.objects.create(
            email_address=self.email,
            code="123456",
            expires_at=timezone.now() + timedelta(minutes=expires_delta_minutes),
        )

    def test_signup_with_valid_code(self):
        self._create_code()

        response = self.client.post(
            self.url,
            {"email_address": self.email, "code": "123456"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLoginData(response)
        self.assertAuthCookies(response)

        account = Account.objects.get(email_address=self.email)

        self.assertTrue(account.is_active)
        self.assertTrue(account.email_verified)

        self.assertFalse(AccessCode.objects.filter(email_address=self.email).exists())

    def test_signup_with_expired_code(self):
        self._create_code(expires_delta_minutes=-5)

        response = self.client.post(
            self.url,
            {"email_address": self.email, "code": "123456"},
        )

        self.assertErrorResponse(response)

        self.assertFalse(Account.objects.filter(email_address=self.email).exists())
