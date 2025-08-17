from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from dj_waanverse_auth import settings
from dj_waanverse_auth.models import VerificationCode
from django.utils import timezone
from datetime import timedelta

Account = get_user_model()


class TestSignup(APITestCase):
    def setUp(self):
        super().setUp()
        mail.outbox = []
        self.signup_url = reverse("dj_waanverse_auth_signup")

        # Existing accounts
        self.user = Account.objects.create_user(
            email_address="test1@gmail.com", email_verified=False
        )
        Account.objects.create_user(
            email_address="test2@gmail.com", email_verified=True
        )

        settings.blacklisted_emails = ["blocked@gmail.com"]

    def test_successful_signup_email(self):
        data = {"email_address": "newuser@gmail.com"}
        response = self.client.post(self.signup_url, data)
        self.assertIn(
            response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK]
        )
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

    def test_missing_email(self):
        response = self.client.post(self.signup_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "email_address",
            response.data,
        )

    def test_invalid_email_format(self):
        response = self.client.post(self.signup_url, {"email_address": "bademail"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Enter a valid email address", str(response.data))

    def test_email_domain_not_allowed(self):
        settings.allowed_email_domains = ["gmail.com"]
        response = self.client.post(self.signup_url, {"email_address": "x@yahoo.com"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email_address", response.data)

    def test_blacklisted_email(self):
        settings.blacklisted_emails = ["blocked@gmail.com"]
        response = self.client.post(
            self.signup_url, {"email_address": "blocked@gmail.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Email address is not allowed", str(response.data))

    def test_existing_verified_email(self):
        response = self.client.post(
            self.signup_url, {"email_address": "test2@gmail.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_existing_unverified_email_reuses_account(self):
        data = {"email_address": "test1@gmail.com"}
        response = self.client.post(self.signup_url, data)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Account.objects.count(), 2)
        self.assertEqual(len(mail.outbox), 1)

    def test_activate_email_success(self):

        VerificationCode.objects.create(
            email_address="test1@gmail.com",
            code="123456",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        data = {
            "email_address": "test1@gmail.com",
            "code": "123456",
        }
        response = self.client.post(self.signup_url, data)
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED]
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)
        self.assertTrue(self.user.is_active)
        self.assertFalse(
            VerificationCode.objects.filter(email_address="test1@gmail.com").exists()
        )
        for key in ["user", "access_token", "refresh_token", "sid"]:
            self.assertIn(key, response.data)

    def test_activate_email_expired_code(self):
        VerificationCode.objects.create(
            email_address="test1@gmail.com",
            code="123456",
            expires_at=timezone.now() - timedelta(minutes=1),  # already expired
        )
        data = {
            "email_address": "test1@gmail.com",
            "code": "123456",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code_expired", str(response.data))
        self.assertFalse(
            VerificationCode.objects.filter(email_address="test1@gmail.com").exists()
        )
