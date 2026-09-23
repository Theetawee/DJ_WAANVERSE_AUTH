# tests/test_session_views.py
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from dj_waanverse_auth.models import Session
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache
from dj_waanverse_auth.utils.security.tokens import issue_tokens_for_account
from tests.utils import generate_rsa_keypair_files

Account = get_user_model()
KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"


class SessionViewsTestCase(TestCase):
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
        self.other_account = Account.objects.create_user(
            email_address="other@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        self.tokens = issue_tokens_for_account(self.account, request=None)

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        clear_key_cache()
        self._tmp.cleanup()

    def auth_get(self, url):
        return self.client.get(
            url, HTTP_AUTHORIZATION=f"Bearer {self.tokens.access_token}"
        )

    def auth_post(self, url):
        return self.client.post(
            url,
            {},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.tokens.access_token}",
        )


class SessionListViewTests(SessionViewsTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("dj_waanverse_auth_sessions")

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_lists_own_active_session(self):
        response = self.auth_get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["sessions"]), 1)
        self.assertEqual(response.data["sessions"][0]["id"], self.tokens.session_id)

    def test_current_session_flagged_correctly(self):
        response = self.auth_get(self.url)
        self.assertTrue(response.data["sessions"][0]["is_current"])

    def test_other_sessions_not_flagged_as_current(self):
        second_tokens = issue_tokens_for_account(self.account, request=None)
        response = self.auth_get(self.url)

        by_id = {s["id"]: s for s in response.data["sessions"]}
        self.assertTrue(by_id[self.tokens.session_id]["is_current"])
        self.assertFalse(by_id[second_tokens.session_id]["is_current"])

    def test_revoked_sessions_excluded_from_list(self):
        Session.objects.get(pk=self.tokens.session_id).revoke()
        response = self.auth_get(self.url)
        self.assertEqual(response.data["sessions"], [])

    def test_only_own_sessions_returned_not_other_accounts(self):
        issue_tokens_for_account(self.other_account, request=None)
        response = self.auth_get(self.url)
        self.assertEqual(len(response.data["sessions"]), 1)

    def test_includes_user_agent_and_ip(self):
        response = self.auth_get(self.url)
        session_data = response.data["sessions"][0]
        self.assertIn("user_agent", session_data)
        self.assertIn("ip_address", session_data)


class SessionRevokeViewTests(SessionViewsTestCase):
    def revoke_url(self, session_id):
        return reverse("dj_waanverse_auth_session_revoke", args=[session_id])

    def test_requires_authentication(self):
        response = self.client.post(self.revoke_url(self.tokens.session_id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_revokes_own_session(self):
        response = self.auth_post(self.revoke_url(self.tokens.session_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session = Session.objects.get(pk=self.tokens.session_id)
        self.assertTrue(session.is_revoked)

    def test_can_revoke_own_session_that_is_not_the_current_one(self):
        second_tokens = issue_tokens_for_account(self.account, request=None)

        response = self.auth_post(self.revoke_url(second_tokens.session_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Session.objects.get(pk=second_tokens.session_id).is_revoked)
        self.assertFalse(Session.objects.get(pk=self.tokens.session_id).is_revoked)

    def test_cannot_revoke_another_accounts_session(self):
        other_tokens = issue_tokens_for_account(self.other_account, request=None)

        response = self.auth_post(self.revoke_url(other_tokens.session_id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Session.objects.get(pk=other_tokens.session_id).is_revoked)

    def test_nonexistent_session_returns_404(self):
        import uuid

        response = self.auth_post(self.revoke_url(uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_same_404_for_missing_and_other_accounts_session(self):
        """The indistinguishability guarantee, checked directly."""
        import uuid

        other_tokens = issue_tokens_for_account(self.other_account, request=None)

        missing = self.auth_post(self.revoke_url(uuid.uuid4()))
        belongs_to_other = self.auth_post(self.revoke_url(other_tokens.session_id))

        self.assertEqual(missing.status_code, belongs_to_other.status_code)
        self.assertEqual(missing.data["msg"], belongs_to_other.data["msg"])

    def test_already_revoked_session_returns_404_not_repeat_success(self):
        Session.objects.get(pk=self.tokens.session_id).revoke()
        response = self.auth_post(self.revoke_url(self.tokens.session_id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RevokeOtherSessionsViewTests(SessionViewsTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("dj_waanverse_auth_revoke_other_sessions")

    def test_requires_authentication(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_revokes_other_sessions_but_not_current_one(self):
        second_tokens = issue_tokens_for_account(self.account, request=None)
        third_tokens = issue_tokens_for_account(self.account, request=None)

        response = self.auth_post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Session.objects.get(pk=self.tokens.session_id).is_revoked)
        self.assertTrue(Session.objects.get(pk=second_tokens.session_id).is_revoked)
        self.assertTrue(Session.objects.get(pk=third_tokens.session_id).is_revoked)

    def test_does_not_touch_other_accounts_sessions(self):
        other_tokens = issue_tokens_for_account(self.other_account, request=None)
        self.auth_post(self.url)
        self.assertFalse(Session.objects.get(pk=other_tokens.session_id).is_revoked)

    def test_reports_correct_count(self):
        issue_tokens_for_account(self.account, request=None)
        issue_tokens_for_account(self.account, request=None)

        response = self.auth_post(self.url)
        self.assertIn("2", response.data["msg"])

    def test_noop_when_no_other_sessions_exist(self):
        response = self.auth_post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Session.objects.get(pk=self.tokens.session_id).is_revoked)
