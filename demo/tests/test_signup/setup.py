from django.urls import reverse

from tests.setup import Setup as Base


class Setup(Base):
    def setUp(self):
        super().setUp()

        self.signup_url = reverse("dj_waanverse_auth_signup")
