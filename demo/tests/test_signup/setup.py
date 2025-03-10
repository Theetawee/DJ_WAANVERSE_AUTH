from django.urls import reverse

from tests.setup import Setup as Base


class Setup(Base):
    def setUp(self):
        super().setUp()

        self.signup_url = reverse("dj_waanverse_auth_signup")
        self.activate_email_url = reverse("dj_waanverse_auth_activate_email")
        self.add_email_url = reverse("dj_waanverse_auth_add_email")
        self.activate_phone_url = reverse("dj_waanverse_auth_activate_phone")
        self.update_account_status_url = reverse(
            "dj_waanverse_auth_update_account_status"
        )
