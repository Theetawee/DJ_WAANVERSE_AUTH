from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse


class TestSetup(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.signup_url = reverse("signup")
