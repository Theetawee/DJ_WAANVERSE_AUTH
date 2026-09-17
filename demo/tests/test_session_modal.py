from django.contrib.auth import get_user_model
from django.test import TestCase

from dj_waanverse_auth.models import Session

Account = get_user_model()


class SessionModelTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
            is_active=True,
        )

    def test_set_and_match_refresh_token(self):
        session = Session.objects.create(account=self.account)
        session.set_refresh_token("raw-token-value")
        session.save()

        self.assertTrue(session.refresh_token_matches("raw-token-value"))
        self.assertFalse(session.refresh_token_matches("wrong-token"))

    def test_raw_token_never_stored(self):
        session = Session.objects.create(account=self.account)
        session.set_refresh_token("super-secret-raw-token")
        session.save()

        self.assertNotIn("super-secret-raw-token", session.refresh_token_hash)

    def test_revoke_sets_flag_and_timestamp(self):
        session = Session.objects.create(account=self.account)
        self.assertFalse(session.is_revoked)
        self.assertIsNone(session.revoked_at)

        session.revoke()

        self.assertTrue(session.is_revoked)
        self.assertIsNotNone(session.revoked_at)
