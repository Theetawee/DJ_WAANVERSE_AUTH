from django.contrib.auth import get_user_model
from django.urls import reverse

from dj_waanverse_auth.models import MultiFactorAuth
from tests.setup import Setup as Base

Account = get_user_model()


class Setup(Base):
    def setUp(self):
        super().setUp()

        self.login_url = reverse("dj_waanverse_auth_login")
        Account.objects.create_user(
            username="axeman",
            email_address="axeman@gmail.com",
            password="testUserP",
        )

        MultiFactorAuth.objects.create(
            account=Account.objects.get(email_address="axeman@gmail.com"),
            activated=True,
            secret_key="gAAAAABngltIBzR1G8-NsWr-71_XOch7bzGQFcURyxxNG5rHAOW1MbcUW3baTBAzvQEW6AorASSbS89m1W3Sj110hgNzHDUJXIDvW5SQbSZcx1pSO6uSZPbEY3ovV_ne-0cBNcWA2jPv",
        )

        self.refresh_access_token_url = reverse(
            "dj_waanverse_auth_refresh_access_token"
        )
        self.logout_url = reverse("dj_waanverse_auth_logout")
        self.get_authenticated_user_url = reverse(
            "dj_waanverse_auth_authenticated_user"
        )

        self.grant_access_url = reverse(
            "dj_waanverse_auth_grant_access",
        )
        self.device_info_url = reverse("dj_waanverse_auth_get_device_info")

        Account.objects.create_user(
            username="test_user1",
            email_address="test_user1@gmail.com",
            password="Test@12",
            phone_number="+256779020674",
            phone_number_verified=True,
            email_verified=True,
        )

        self.user_1_email_login_data = {
            "login_field": "test_user1@gmail.com",
            "password": "Test@12",
            "login_method": "email_address",
        }
        self.test_user_1 = Account.objects.get(username="test_user1")
        self.user_1_username_login_data = {
            "login_field": "test_user1",
            "password": "Test@12",
            "login_method": "username",
        }
