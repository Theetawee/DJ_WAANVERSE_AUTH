from rest_framework_simplejwt.settings import api_settings

from dj_waanverse_auth.settings import accounts_config

from .test_setup import TestSetup


class TestCookies(TestSetup):
    def test_access_cookie(self):
        user_data = {"login_field": self.user2.username, "password": "password2"}
        response = self.client.post(self.login_url, user_data, format="json")

        # Check if authentication cookies are set
        self.assert_auth_cookies(response=response)

        # Extract the cookie from the response
        cookie_name = accounts_config.ACCESS_TOKEN_COOKIE
        cookie = response.cookies.get(cookie_name)

        # Test the presence of the cookie
        self.assertIsNotNone(cookie, f"{cookie_name} cookie is not set in the response")

        # Test the cookie's max-age
        cookie_max_age = int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds())
        self.assertEqual(
            cookie["max-age"],
            cookie_max_age,
            f"Expected max-age to be {cookie_max_age}, but got {cookie['max-age']}",
        )

        # Test if the cookie is HttpOnly
        self.assertEqual(cookie.get("httponly"), accounts_config.COOKIE_HTTP_ONLY_FLAG)

        # Test the cookie's path
        self.assertEqual(cookie["path"], "/", "Cookie path is not set to '/'")

        # Test the cookie's domain
        cookie_domain = accounts_config.COOKIE_DOMAIN
        if cookie_domain:
            self.assertEqual(
                cookie["domain"],
                cookie_domain,
                f"Expected domain to be {cookie_domain}, but got {cookie['domain']}",
            )

        # Test the SameSite policy
        self.assertEqual(cookie.get("samesite"), accounts_config.COOKIE_SAMESITE_POLICY)

    def test_refresh_cookie(self):
        user_data = {"login_field": self.user2.username, "password": "password2"}
        response = self.client.post(self.login_url, user_data, format="json")

        # Check if authentication cookies are set
        self.assert_auth_cookies(response=response)

        # Extract the refresh cookie from the response
        cookie_name = accounts_config.REFRESH_TOKEN_COOKIE
        cookie = response.cookies.get(cookie_name)

        # Test the presence of the cookie
        self.assertIsNotNone(cookie, f"{cookie_name} cookie is not set in the response")

        # Test the cookie's max-age
        cookie_max_age = int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds())
        self.assertEqual(
            cookie["max-age"],
            cookie_max_age,
            f"Expected max-age to be {cookie_max_age}, but got {cookie['max-age']}",
        )

        # Test if the cookie is HttpOnly
        self.assertEqual(cookie.get("httponly"), accounts_config.COOKIE_HTTP_ONLY_FLAG)

        # Test the cookie's path
        self.assertEqual(cookie["path"], "/", "Cookie path is not set to '/'")

        # Test the cookie's domain
        cookie_domain = accounts_config.COOKIE_DOMAIN
        if cookie_domain:
            self.assertEqual(
                cookie["domain"],
                cookie_domain,
                f"Expected domain to be {cookie_domain}, but got {cookie['domain']}",
            )

        # Test the SameSite policy
        self.assertEqual(cookie.get("samesite"), accounts_config.COOKIE_SAMESITE_POLICY)

    def test_refresh_token(self):
        user_data = {"login_field": self.user2.username, "password": "password2"}

        res = self.client.post(self.login_url, user_data, format="json")

        self.assert_auth_cookies(response=res)
        self.assert_auth_response(response=res)

        response = self.client.post(self.refresh_token_url)
        self.assertIn("access_token", response.data)
        self.assertNotEqual(
            res.cookies[accounts_config.ACCESS_TOKEN_COOKIE].value,
            response.cookies[accounts_config.ACCESS_TOKEN_COOKIE].value,
        )

    def test_refresh_token_no_refresh_token(self):
        response = self.client.post(self.refresh_token_url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("msg", response.data)
        self.assertEqual(response.data["msg"], "Refresh token is required.")
