import re
from urllib.parse import parse_qs, urlparse

from django.core import mail
from rest_framework import status

from dj_waanverse_auth import settings

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

        email_body = mail.outbox[0].body
        confirmation_link_match = re.search(r"https?://[^\s]+", email_body)

        if confirmation_link_match:
            confirmation_link = confirmation_link_match.group(0)
        else:
            confirmation_link = None
        self.assertIsNotNone(confirmation_link)
        parsed_url = urlparse(confirmation_link)
        token = parse_qs(parsed_url.query).get("token", [None])[0]
        print(token)
