from datetime import timedelta

from django.core import mail
from django.utils import timezone
from rest_framework import status

from dj_waanverse_auth import settings
from dj_waanverse_auth.models import VerificationCode

from .test_setup import TestSetup


class TestSignup(TestSetup):
    def test_signup_short_password(self):
        data = {
            "username": "test_user",
            "password": "Test@12",
            "confirm_password": "Test@12",
            "name": "test_user",
        }

        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "This password is too short. It must contain at least 8 characters.",
            response.data["non_field_errors"],
        )

    def test_signup_weak_password(self):
        data = {
            "username": "test_user",
            "password": "Test12",
            "confirm_password": "Test12",
            "name": "test_user",
        }

        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup(self):
        data = {
            "username": "test_user",
            "password": "Test@1220",
            "confirm_password": "Test@1220",
            "name": "test_user",
        }

        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class TestAddEmail(TestSetup):
    def test_add_email_unauthenticated(self):
        data = {
            "email_address": "test@gmail.com",
        }

        response = self.client.post(self.add_email_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_email_authenticated(self):
        self.client.force_authenticate(user=self.user2)
        data = {"email_address": "test@gmail.com"}

        response = self.client.post(self.add_email_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, settings.verification_email_subject)
        verification_code = VerificationCode.objects.filter(
            email_address=data["email_address"]
        ).first()
        email_body = mail.outbox[0].body
        self.assertIn(verification_code.code, email_body)

    def test_add_existing_email(self):
        self.client.force_authenticate(user=self.user2)
        data = {"email_address": "axeman@gmail.com"}

        response = self.client.post(self.add_email_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)


class TestActivateEmail(TestSetup):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user2)

    def test_activate_email(self):
        data = {"email_address": "test@gmail.com"}
        self.client.post(self.add_email_url, data)
        code = VerificationCode.objects.get(email_address=data["email_address"]).code

        response = self.client.post(
            self.activate_email_url,
            data={"email_address": "test@gmail.com", "code": code},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user2.email_address, "test@gmail.com")
        self.assertEqual(
            VerificationCode.objects.filter(email_address="test@gmail.com").count(), 0
        )
        self.assertTrue(self.user2.email_verified)

    def test_activate_invalid_code(self):
        data = {"email_address": "test@gmail.com"}
        self.client.post(self.add_email_url, data)

        response = self.client.post(
            self.activate_email_url,
            data={"email_address": "test@gmail.com", "code": "00000"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.user2.email_address, None)
        self.assertEqual(
            VerificationCode.objects.filter(email_address="test@gmail.com").count(), 1
        )

    def test_activate_expired_code(self):
        data = {"email_address": "test@gmail.com"}
        self.client.post(self.add_email_url, data)

        verification_code = VerificationCode.objects.get(
            email_address=data["email_address"]
        )

        verification_code.created_at = timezone.now() - timedelta(
            minutes=settings.verification_email_code_expiry_in_minutes
        )
        verification_code.save(update_fields=["created_at"])

        response = self.client.post(
            self.activate_email_url,
            data={"email_address": "test@gmail.com", "code": verification_code.code},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(self.user2.email_address, "test@gmail.com")


class TestAddPhone(TestSetup):
    def test_add_phone_unauthenticated(self):
        data = {
            "phone_number": "+256779736255",
        }

        response = self.client.post(self.add_phone_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_phone_authenticated(self):
        self.client.force_authenticate(user=self.user2)
        data = {"phone_number": "+256779736255"}

        response = self.client.post(self.add_phone_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_existing_phone(self):
        self.client.force_authenticate(user=self.user2)
        data = {"phone_number": "+256779020674"}

        response = self.client.post(self.add_phone_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
