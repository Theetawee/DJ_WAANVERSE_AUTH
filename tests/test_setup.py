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
        self.login_url = reverse("dj_waanverse_auth_login")
        self.signup_url = reverse("dj_waanverse_auth_signup")
        self.client = APIClient()
        self.user_1_email_login_data = {"login_field": "test_user1@gmail.com", "password": "Test@12"}
        self.user_1_username_login_data = {"login_field": "test_user1", "password": "Test@12"}
        self.user_1_phone_login_data = {
            "login_field": "256779020674",
            "password": "Test@12",
        }

        self.test_user_1 = Account.objects.get(username="test_user1")
        mail.outbox = []
        return super().setUp()
