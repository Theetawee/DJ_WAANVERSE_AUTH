from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from dj_waanverse_auth import settings
from dj_waanverse_auth.models import VerificationCode

Account = get_user_model()


class TestSignup(APITestCase):
    def setUp(self):
        super().setUp()
        mail.outbox = []
        self.signup_url = reverse("dj_waanverse_auth_signup")

    def test_successful_signup(self):
        data = {
            "email_address": "test@gmail.com",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Account.objects.filter(
                email_address=data["email_address"], email_verified=False
            ).exists()
        )
        sent_mail = mail.outbox[0]
        self.assertEqual(sent_mail.to, [data["email_address"]])
        self.assertEqual(sent_mail.subject, settings.verification_email_subject)

        verification_code = VerificationCode.objects.get(
            email_address=data["email_address"]
        ).code

        self.assertIn(verification_code, sent_mail.body)
