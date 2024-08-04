from .test_setup import TestSetup
from rest_framework import status


class LoginViewTests(TestSetup):

    def test_login_with_username(self):
        response = self.client.post(
            self.url,
            {
                "login_field": "testuser",
                "password": "testpassword123",
            },
        )
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn(self.access_cookie_name, response.cookies)
        self.assertIn(self.refresh_cookie_name, response.cookies)

        # Retrieve the cookies
        access_cookie = response.cookies[self.access_cookie_name]
        refresh_cookie = response.cookies[self.refresh_cookie_name]

        # Assert that cookies are set and have the correct attributes
        self.assertTrue(access_cookie)
        self.assertTrue(refresh_cookie)
        self.assertEqual(access_cookie["httponly"], True)
        self.assertEqual(refresh_cookie["httponly"], True)

        # Assert that the cookie values match the response data
        self.assertEqual(access_cookie.value, response.data["access_token"])
        self.assertEqual(refresh_cookie.value, response.data["refresh_token"])
