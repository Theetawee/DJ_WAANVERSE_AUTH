from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core import mail
from unittest.mock import patch
from dj_waanverse_auth.models import AccessCode
from dj_waanverse_auth import settings

Account = get_user_model()


class SignupTests(APITestCase):
    def setUp(self):
        self.signup_url = reverse("dj_waanverse_auth_auth")
        mail.outbox = []

        # Default mock config values
        self.allowed_domains_patch = patch(
            "dj_waanverse_auth.settings.allowed_email_domains",
            ["gmail.com", "outlook.com"],
        )
        self.blacklisted_emails_patch = patch(
            "dj_waanverse_auth.settings.blacklisted_emails", ["banned@gmail.com"]
        )

        self.allowed_domains_patch.start()
        self.blacklisted_emails_patch.start()

    def tearDown(self):
        patch.stopall()

    def test_successful_signup_email(self):
        """User can sign up with a valid new email."""
        data = {"email_address": "new@gmail.com"}
        response = self.client.post(self.signup_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Account.objects.filter(email_address="new@gmail.com").exists())
        self.assertFalse(Account.objects.get(email_address="new@gmail.com").is_active)
        self.assertFalse(
            Account.objects.get(email_address="new@gmail.com").email_verified
        )

        self.assertEqual(len(mail.outbox), 1)
        sent_mail = mail.outbox[0]
        self.assertEqual(sent_mail.to, ["new@gmail.com"])
        self.assertTrue(
            AccessCode.objects.filter(email_address="new@gmail.com").exists()
        )
        code = AccessCode.objects.get(email_address="new@gmail.com").code
        self.assertIn(code, sent_mail.body)

    def test_invalid_email_format(self):
        """Reject invalid email formats."""
        data = {"email_address": "invalid-email"}
        response = self.client.post(self.signup_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual("Invalid email address", response.data["detail"])

    def test_disallowed_domain(self):
        """Reject emails from disallowed domains."""
        data = {"email_address": "user@yahoo.com"}  # yahoo.com not in allowed list
        response = self.client.post(self.signup_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual("Invalid email address", response.data["detail"])

    def test_blacklisted_email(self):
        """Reject blacklisted email addresses."""
        data = {"email_address": "banned@gmail.com"}
        response = self.client.post(self.signup_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual("Invalid email address", response.data["detail"])

    def test_existing_user_returns_existing(self):
        """Existing user should not cause a duplicate error."""
        Account.objects.create(email_address="existing@gmail.com")
        data = {"email_address": "existing@gmail.com"}
        response = self.client.post(self.signup_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Account.objects.count(), 1)

    @patch("dj_waanverse_auth.settings.allowed_email_domains", None)
    def test_signup_without_allowed_domains(self):
        """Signup should pass when allowed domains list is not set."""
        data = {"email_address": "freeuser@yahoo.com"}
        response = self.client.post(self.signup_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            Account.objects.filter(email_address="freeuser@yahoo.com").exists()
        )

    def test_signup_and_authentication(self):
        AccessCode.objects.all().delete()
        self.client.post(self.signup_url, {"email_address": "test@gmail.com"})
        access_code = AccessCode.objects.get(email_address="test@gmail.com").code

        response = self.client.post(
            self.signup_url, {"email_address": "test@gmail.com", "code": access_code}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn(settings.access_token_cookie, response.data)
        self.assertIn(settings.refresh_token_cookie, response.data)
        self.assertIn("sid", response.data)

        self.assertIn("user", response.data)

        self.assertIn(settings.access_token_cookie, response.cookies)
        self.assertIn(settings.refresh_token_cookie, response.cookies)
