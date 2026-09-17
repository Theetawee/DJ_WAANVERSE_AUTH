import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from dj_waanverse_auth.models import Session
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache
from dj_waanverse_auth.utils.security.tokens import (
    RefreshError,
    issue_tokens_for_account,
    rotate_refresh_token,
)
from tests.utils import generate_rsa_keypair_files

Account = get_user_model()
KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"


class TokensTestCase(TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        private_path, public_path = generate_rsa_keypair_files(Path(self._tmp.name))

        self.patchers = [
            patch(f"{KEYS_MODULE}.private_key_path", private_path),
            patch(f"{KEYS_MODULE}.public_key_path", public_path),
        ]
        for p in self.patchers:
            p.start()
        clear_key_cache()

        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
            is_active=True,
        )

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        clear_key_cache()
        self._tmp.cleanup()

    def _fake_request(self, user_agent="TestAgent/1.0", ip="203.0.113.5"):
        request = MagicMock()
        request.META = {"HTTP_USER_AGENT": user_agent}
        request.ip_address = ip
        return request

    def test_issue_tokens_creates_session(self):
        self.assertEqual(Session.objects.count(), 0)

        tokens = issue_tokens_for_account(self.account, request=self._fake_request())

        self.assertEqual(Session.objects.count(), 1)
        session = Session.objects.get()
        self.assertEqual(session.account_id, self.account.pk)
        self.assertTrue(session.refresh_token_matches(tokens.refresh_token))

    def test_issue_tokens_without_request_still_works(self):
        tokens = issue_tokens_for_account(self.account, request=None)

        session = Session.objects.get()
        self.assertEqual(session.user_agent, "")
        self.assertIsNone(session.ip_address)
        self.assertTrue(tokens.access_token)

    def test_rotate_issues_new_pair_for_same_session(self):
        tokens = issue_tokens_for_account(self.account, request=self._fake_request())

        new_tokens = rotate_refresh_token(tokens.refresh_token)

        self.assertNotEqual(new_tokens.access_token, tokens.access_token)
        self.assertNotEqual(new_tokens.refresh_token, tokens.refresh_token)
        self.assertEqual(new_tokens.session_id, tokens.session_id)

    def test_rotate_updates_session_hash(self):
        tokens = issue_tokens_for_account(self.account, request=self._fake_request())

        new_tokens = rotate_refresh_token(tokens.refresh_token)

        session = Session.objects.get(pk=tokens.session_id)
        self.assertTrue(session.refresh_token_matches(new_tokens.refresh_token))
        self.assertFalse(session.refresh_token_matches(tokens.refresh_token))

    def test_reusing_a_rotated_refresh_token_revokes_the_session(self):
        tokens = issue_tokens_for_account(self.account, request=self._fake_request())
        rotate_refresh_token(tokens.refresh_token)  # legitimate rotation

        with self.assertRaises(RefreshError):
            rotate_refresh_token(tokens.refresh_token)  # replay of the superseded token

        session = Session.objects.get(pk=tokens.session_id)
        self.assertTrue(session.is_revoked)

    def test_rotate_rejects_already_revoked_session(self):
        tokens = issue_tokens_for_account(self.account, request=self._fake_request())
        Session.objects.get(pk=tokens.session_id).revoke()

        with self.assertRaises(RefreshError):
            rotate_refresh_token(tokens.refresh_token)

    def test_rotate_rejects_access_token_used_as_refresh_token(self):
        tokens = issue_tokens_for_account(self.account, request=self._fake_request())

        with self.assertRaises(RefreshError):
            rotate_refresh_token(tokens.access_token)

    def test_rotate_rejects_garbage_input(self):
        with self.assertRaises(RefreshError):
            rotate_refresh_token("not-a-real-jwt-at-all")

    def test_rotate_rejects_token_whose_session_no_longer_exists(self):
        tokens = issue_tokens_for_account(self.account, request=self._fake_request())
        Session.objects.filter(pk=tokens.session_id).delete()

        with self.assertRaises(RefreshError):
            rotate_refresh_token(tokens.refresh_token)
