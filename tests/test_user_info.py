from .test_setup import TestSetup
from rest_framework import status


class TestUserInfo(TestSetup):
    def test_user_info(self):
        self.client.post(
            self.url,
            {
                "login_field": "testuser2",
                "password": "testpassword123",
            },
        )
        response = self.client.get(self.userInfo_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
