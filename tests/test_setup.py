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
        self.initiate_email_verification_url = reverse(
            "dj_waanverse_auth_initiate_email_verification"
        )
        self.home_page_url = reverse("dj_waanverse_auth_home_page")
        self.verify_email_url = reverse("dj_waanverse_auth_verify_email")
        self.get_mfa_secret_view_url = reverse("dj_waanverse_auth_get_mfa_secret")
        self.activate_mfa_url = reverse("dj_waanverse_auth_activate_mfa")
        self.mfa_login_url = reverse("dj_waanverse_auth_mfa_login")
        self.deactivate_mfa_url = reverse("dj_waanverse_auth_deactivate_mfa")
        self.client = APIClient()
        self.user_1_email_login_data = {
            "login_field": "test_user1@gmail.com",
            "password": "Test@12",
        }
        self.user_1_username_login_data = {
            "login_field": "test_user1",
            "password": "Test@12",
        }
        self.user_1_phone_login_data = {
            "login_field": "256779020674",
            "password": "Test@12",
        }

        self.test_user_1 = Account.objects.get(username="test_user1")
        self.test_user_with_mfa = Account.objects.get(username="axeman")
        self.test_user_with_mfa_login_data = {
            "login_field": "axeman",
            "password": "testUserP",
        }
        mail.outbox = []
        return super().setUp()
