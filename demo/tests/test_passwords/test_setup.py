from django.contrib.auth import get_user_model
from django.urls import reverse

from tests.setup import Setup as Base

Account = get_user_model()


class Setup(Base):
    def setUp(self):
        super().setUp()

        self.login_url = reverse("dj_waanverse_auth_login")

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
        self.user_1_username_login_data = {
            "login_field": "test_user1",
            "password": "Test@12",
            "login_method": "username",
        }
        self.user_1_phone_login_data = {
            "login_field": "+256779020674",
            "password": "Test@12",
            "login_method": "phone_number",
        }
        self.test_user_1 = Account.objects.get(username="test_user1")
        self.initiate_password_reset_url = reverse(
            "dj_waanverse_auth_initiate_password_reset"
        )
        self.reset_new_password_url = reverse("dj_waanverse_auth_reset_password")
        self.get_authenticated_user_url = reverse(
            "dj_waanverse_auth_authenticated_user"
        )
