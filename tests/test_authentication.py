from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from tests.base import BaseAPITestCase

Account = get_user_model()


class AuthenticationTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.email = "test_user@gmail.com"
        self.me_url = reverse("dj_waanverse_auth_me")
        self.account = Account.objects.create_user(email_address=self.email)

        self.client.force_authenticate(self.account)

    def test_get_logged_in_user_info(self):
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.email, response.data["email_address"])
