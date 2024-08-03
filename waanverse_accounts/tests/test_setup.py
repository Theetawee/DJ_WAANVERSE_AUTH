from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from waanverse_accounts.models import Account
from django.conf import settings


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
            phone="1234567890",
        )
        self.access_cookie_name = settings.BROWSER_CONFIG["ACCESS_COOKIE_NAME"]
        self.refresh_cookie_name = settings.BROWSER_CONFIG["REFRESH_COOKIE_NAME"]
        self.url = reverse("login")
        return super().setUp()
