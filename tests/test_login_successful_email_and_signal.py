from .test_setup import TestSetup
from dj_waanverse_auth.settings import accounts_config
from django.core import mail
from dj_waanverse_auth.models import UserLoginActivity


class LoginViewTests(TestSetup):

    def test_login_verified(self):
        accounts_config["EMAIL_ON_LOGIN"] = True

        response = self.client.post(
            self.url,
            {
                "login_field": "testuser2",
                "password": "testpassword123",
            },
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "New Login Alert")
        self.assertEqual(mail.outbox[0].to, ["test2@example.com"])
        self.assertEqual(UserLoginActivity.objects.count(), 1)
        self.assertEqual(UserLoginActivity.objects.first().login_username, "testuser2")
        self.assert_tokens_and_cookies(response)

    def test_login_no_login_email(self):
        accounts_config["EMAIL_ON_LOGIN"] = False

        response = self.client.post(
            self.url,
            {
                "login_field": "testuser2",
                "password": "testpassword123",
            },
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(UserLoginActivity.objects.count(), 1)
        self.assertEqual(UserLoginActivity.objects.first().login_username, "testuser2")
        self.assert_tokens_and_cookies(response)
