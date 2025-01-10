import os

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class TestSetup(TestCase):

    fixtures = [os.path.join(settings.BASE_DIR, "fixtures/users.json")]

    def setUp(self):
        self.login_url = reverse("dj_waanverse_auth_login")
        self.client = APIClient()

        return super().setUp()
