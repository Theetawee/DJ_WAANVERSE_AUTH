from django.core import mail

from dj_waanverse_auth.settings import accounts_config

from .test_setup import TestSetup


class TestLoginView(TestSetup):
    def test_login_view_non_verified(self):
        mail.outbox = []
        accounts_config.AUTH_METHODS = ["username"]
        accounts_config.EMAIL_THREADING_ENABLED = False
        user_data = {
            "login_field": self.user1.username,
            "password": "password1",
        }
        response = self.client.post(self.login_url, user_data, format="json")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], self.user1.email)
        self.assertEqual(mail.outbox[0].subject, self.messages.verify_email_subject)
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.data)
        self.assertIn("msg", response.data)
        self.assertEqual(response.data["msg"], self.messages.status_unverified)
        self.assertEqual(response.data["email"], self.user1.email)

    def test_login_view_verified_email(self):
        accounts_config.AUTH_METHODS = ["email"]
        user_data = {
            "login_field": self.user2.email,
            "password": "password2",
        }
        response = self.client.post(self.login_url, user_data, format="json")
        self.assert_auth_cookies(response)
        self.assert_auth_response(response)

    def test_login_view_verified_phone_number(self):
        accounts_config.AUTH_METHODS = ["phone_number"]
        user_data = {
            "login_field": self.user1.phone_number,
            "password": "password1",
        }
        response = self.client.post(self.login_url, user_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.data)
        self.assertIn("msg", response.data)
        self.assertEqual(response.data["msg"], self.messages.status_unverified)
        self.assertEqual(response.data["email"], self.user1.email)

    def test_logout(self):
        accounts_config.AUTH_METHODS = ["username"]
        self.client.post(
            self.login_url,
            {"login_field": self.user2.username, "password": "password2"},
            format="json",
        )
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("msg", response.data)
        self.assertEqual(response.data["msg"], self.messages.logout_successful)

    def test_login_view_email_on_login(self):
        accounts_config.AUTH_METHODS = ["email"]
        accounts_config.EMAIL_THREADING_ENABLED = False
        accounts_config.ENABLE_EMAIL_ON_LOGIN = True
        mail.outbox = []
        user_data = {
            "login_field": self.user2.email,
            "password": "password2",
        }
        response = self.client.post(self.login_url, user_data, format="json")
        self.assert_auth_cookies(response)
        self.assert_auth_response(response)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], self.user2.email)
        self.assertEqual(mail.outbox[0].subject, self.messages.login_email_subject)
