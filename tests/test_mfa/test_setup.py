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
        self.test_user_with_mfa = Account.objects.get(username="axeman")
        self.test_user_with_mfa_login_data = {
            "login_field": "axeman",
            "password": "testUserP",
            "login_method": "username",
        }

        self.get_mfa_secret_view_url = reverse("dj_waanverse_auth_get_mfa_secret")
        self.activate_mfa_url = reverse("dj_waanverse_auth_activate_mfa")
        self.mfa_login_url = reverse("dj_waanverse_auth_mfa_login")
        self.deactivate_mfa_url = reverse("dj_waanverse_auth_deactivate_mfa")
        self.generate_mfa_recovery_codes_url = reverse(
            "dj_waanverse_auth_generate_recovery_codes"
        )
        self.get_recovery_codes_url = reverse("dj_waanverse_auth_get_recovery_codes")
