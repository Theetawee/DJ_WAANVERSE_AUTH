from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from dj_waanverse_auth import settings
from dj_waanverse_auth.models import VerificationCode
from unittest.mock import patch

Account = get_user_model()


class TestSignup(APITestCase):
    def setUp(self):
        super().setUp()
        mail.outbox = []
        self.signup_url = reverse("dj_waanverse_auth_signup")

        # Existing accounts
        Account.objects.create_user(
            email_address="test1@gmail.com", email_verified=False
        )
        Account.objects.create_user(
            email_address="test2@gmail.com", email_verified=True
        )

        # For phone
        Account.objects.create_user(
            phone_number="+256779820542", phone_number_verified=False
        )
        Account.objects.create_user(
            phone_number="+922222222222", phone_number_verified=True
        )

        settings.blacklisted_emails = ["blocked@gmail.com"]
        settings.blacklisted_phone_numbers = ["+933333333333"]

    def test_successful_signup_email(self):
        data = {"email_address": "newuser@gmail.com"}
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Account.objects.filter(
                email_address=data["email_address"],
                email_verified=False,
                is_active=False,
            ).exists()
        )
        sent_mail = mail.outbox[0]
        self.assertEqual(sent_mail.to, [data["email_address"]])
        self.assertEqual(sent_mail.subject, settings.verification_email_subject)
        verification_code = VerificationCode.objects.get(
            email_address=data["email_address"]
        ).code
        self.assertIn(verification_code, sent_mail.body)

    def test_successful_signup_phone(self):
        data = {"phone_number": "+911234567890"}
        with patch("accounts.utils.send_phone_code") as mock_send:
            response = self.client.post(self.signup_url, data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(
                Account.objects.filter(
                    phone_number=data["phone_number"],
                    phone_number_verified=False,
                    is_active=False,
                ).exists()
            )
            mock_send.assert_called_once()

    def test_missing_email_and_phone(self):
        response = self.client.post(self.signup_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "You must provide either an email address or a phone number.",
            str(response.data),
        )

    def test_invalid_email_format(self):
        response = self.client.post(self.signup_url, {"email_address": "bademail"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Enter a valid email address", str(response.data))

    def test_email_domain_not_allowed(self):
        settings.allowed_email_domains = ["gmail.com"]
        response = self.client.post(self.signup_url, {"email_address": "x@yahoo.com"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid email address", str(response.data))

    def test_blacklisted_email(self):
        settings.blacklisted_emails = ["blocked@gmail.com"]
        response = self.client.post(
            self.signup_url, {"email_address": "blocked@gmail.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Email address is not allowed", str(response.data))

    def test_invalid_phone_format(self):
        response = self.client.post(self.signup_url, {"phone_number": "12345"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid phone number format", str(response.data))

    def test_blacklisted_phone(self):
        settings.blacklisted_phone_numbers = ["+933333333333"]
        response = self.client.post(self.signup_url, {"phone_number": "+933333333333"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_existing_verified_email(self):
        response = self.client.post(
            self.signup_url, {"email_address": "test2@gmail.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_existing_verified_phone(self):
        response = self.client.post(self.signup_url, {"phone_number": "+922222222222"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_existing_unverified_email_reuses_account(self):
        data = {"email_address": "test1@gmail.com"}
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Account.objects.count(), 4)  # no duplicate user
        self.assertEqual(len(mail.outbox), 1)

    def test_existing_unverified_phone_reuses_account(self):
        data = {"phone_number": "+256779820542"}
        with patch("accounts.utils.send_phone_code") as mock_send:
            response = self.client.post(self.signup_url, data)
            print(response.data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(Account.objects.count(), 4)
            mock_send.assert_called_once()
