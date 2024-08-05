from .test_setup import TestSetup
from dj_waanverse_auth.settings import accounts_config


class LoginViewTests(TestSetup):

    def test_login_unverified(self):
        accounts_config["VERIFY_EMAIL"] = False

        response = self.client.post(
            self.url,
            {
                "login_field": "testuser",
                "password": "testpassword",
            },
        )
        self.assert_tokens_and_cookies(response)

    def test_login_verified(self):
        accounts_config["VERIFY_EMAIL"] = True

        response = self.client.post(
            self.url,
            {
                "login_field": "testuser2",
                "password": "testpassword123",
            },
        )
        self.assert_tokens_and_cookies(response)
