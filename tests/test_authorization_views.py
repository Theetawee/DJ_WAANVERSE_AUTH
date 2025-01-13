from rest_framework import status

from dj_waanverse_auth.settings import auth_config

from .test_setup import TestSetup


class TestAuthorizationViews(TestSetup):

    def test_refresh_access_token_use_cookie(self):
        self.client.post(self.login_url, data=self.user_1_email_login_data)

        response = self.client.post(
            self.refresh_access_token_url,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)

    def test_refresh_access_token_use_token(self):
        login_response = self.client.post(
            self.login_url, data=self.user_1_email_login_data
        )
        refresh_token = login_response.data["refresh_token"]

        # remove cookie
        self.client.cookies.pop(
            auth_config.refresh_token_cookie,
        )

        response = self.client.post(
            self.refresh_access_token_url,
            data={"refresh_token": refresh_token},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)

    def test_refresh_access_token_no_token(self):
        self.client.post(self.login_url, data=self.user_1_email_login_data)

        # remove cookie
        self.client.cookies.pop(
            auth_config.refresh_token_cookie,
        )

        response = self.client.post(
            self.refresh_access_token_url,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout(self):
        self.client.post(
            self.login_url, data=self.user_1_email_login_data
        )

        response = self.client.post(
            self.logout_url
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for cookie_name in response.cookies:
            self.assertEqual(
                response.cookies[cookie_name].value,
                "",
                f"Cookie {cookie_name} was not removed",
            )

    def test_get_authenticated_user(self):
        self.client.post(self.login_url, data=self.user_1_email_login_data)

        response = self.client.get(self.get_authenticated_user_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.test_user_1.username)
