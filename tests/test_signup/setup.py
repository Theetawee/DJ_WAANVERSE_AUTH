from django.urls import reverse

from tests.setup import Setup as Base


class Setup(Base):
    def setUp(self):
        super().setUp()

        self.signup_url = reverse("dj_waanverse_auth_signup")
        self.activate_email_url = reverse("dj_waanverse_auth_activate_email")
        self.verify_email_address_url = reverse(
            "dj_waanverse_auth_send_email_verification_code"
        )
        self.send_phone_verification_code_url = reverse(
            "dj_waanverse_auth_send_phone_number_verification_code"
        )
        self.activate_phone_url = reverse("dj_waanverse_auth_activate_phone")
