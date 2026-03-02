from rest_framework.test import APITestCase
from rest_framework import status
from dj_waanverse_auth import settings


from copy import deepcopy
from dj_waanverse_auth import settings as auth_config


class BaseAPITestCase(APITestCase):

    def setUp(self):
        super().setUp()
        # Snapshot original config to avoid test bleed
        self._original_config = deepcopy(auth_config.__dict__)

    def tearDown(self):
        # Restore original config
        for key, value in self._original_config.items():
            setattr(auth_config, key, value)

    def assertLoginData(self, response, status_code=status.HTTP_200_OK):
        self.assertEqual(response.status_code, status_code)

        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn("user", response.data)

        user = response.data["user"]

        self.assertIn("id", user)
        self.assertIn("email_address", user)

        return True

    def assertErrorResponse(self, response, status_code=status.HTTP_400_BAD_REQUEST):
        self.assertEqual(response.status_code, status_code)
        self.assertIn("detail", response.data)
        return True

    def assertAuthCookies(self, response):
        self.assertIn(settings.access_token_cookie, response.cookies)
        self.assertIn(settings.refresh_token_cookie, response.cookies)

        access = response.cookies[settings.access_token_cookie]
        refresh = response.cookies[settings.refresh_token_cookie]

        self.assertTrue(access.value)
        self.assertTrue(refresh.value)

        self.assertTrue(access["httponly"])
        self.assertTrue(refresh["httponly"])

        return True
