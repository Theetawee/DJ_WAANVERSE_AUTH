from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from accounts.models import Account
from dj_waanverse_auth.settings import accounts_config


accounts_config["AUTHENTICATION_METHODS"] = ["username"]


class TestSetup(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = Account.objects.create_user(
            email="test@example.com",
            username="testuser",
            name="Test User",
            password="testpassword123",
            date_of_birth="1990-01-01",
            pronouns="H",
            phone_number="1234567890",
        )
        self.access_cookie_name = accounts_config["ACCESS_TOKEN_COOKIE_NAME"]
        self.refresh_cookie_name = accounts_config["REFRESH_TOKEN_COOKIE_NAME"]
        self.url = reverse("login")
        return super().setUp()
