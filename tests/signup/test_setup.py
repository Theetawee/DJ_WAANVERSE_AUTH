from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class TestSetup(TestCase):
    def setUp(self):
        self.signup_url = reverse("dj_waanverse_auth_signup")
        self.client = APIClient()
        return super().setUp()
