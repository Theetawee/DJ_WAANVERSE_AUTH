import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

Account = get_user_model()


class TestSetup(TestCase):
    fixtures = [os.path.join(settings.BASE_DIR, "fixtures/users.json")]

    def setUp(self):
        self.signup_url = reverse("dj_waanverse_auth_signup")
        self.add_email_url = reverse("dj_waanverse_auth_add_email")
        self.activate_email_url = reverse("dj_waanverse_auth_activate_email")
        self.user2 = Account.objects.get(id=3)
        self.user2_data = {
            "username": "test_user",
            "password": "Test@12",
        }
        self.client = APIClient()
        mail.outbox = []
        return super().setUp()
