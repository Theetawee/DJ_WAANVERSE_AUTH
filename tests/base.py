from rest_framework.test import APITestCase
from rest_framework import status
from dj_waanverse_auth import settings


from copy import deepcopy
from dj_waanverse_auth import settings as auth_config


class BaseAPITestCase(APITestCase):

    def setUp(self):
        super().setUp()
        self._original_auth_config = {
            "disable_signup": auth_config.disable_signup,
            "blacklisted_emails": deepcopy(auth_config.blacklisted_emails),
            "blacklisted_email_domains": deepcopy(
                auth_config.blacklisted_email_domains
            ),
            "allowed_email_domains": deepcopy(auth_config.allowed_email_domains),
            "testing_email_addresses": deepcopy(auth_config.testing_email_addresses),
            "is_testing": auth_config.is_testing,
        }

    def tearDown(self):
        auth_config.disable_signup = self._original_auth_config["disable_signup"]
        auth_config.blacklisted_emails = self._original_auth_config[
            "blacklisted_emails"
        ]
        auth_config.blacklisted_email_domains = self._original_auth_config[
            "blacklisted_email_domains"
        ]
        auth_config.allowed_email_domains = self._original_auth_config[
            "allowed_email_domains"
        ]
        auth_config.testing_email_addresses = self._original_auth_config[
            "testing_email_addresses"
        ]
        auth_config.is_testing = self._original_auth_config["is_testing"]

        super().tearDown()

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
