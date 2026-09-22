# tests/test_refresh_view.py
from __future__ import annotations

import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from dj_waanverse_auth.models import Session
from dj_waanverse_auth.utils.security.jwt import encode_token
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache
from dj_waanverse_auth.utils.security.tokens import issue_tokens_for_account
from tests.utils import generate_rsa_keypair_files

Account = get_user_model()
KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"


class RefreshViewTests(TestCase):
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

        self.url = reverse("dj_waanverse_auth_refresh")
        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        self.tokens = issue_tokens_for_account(self.account, request=None)

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        clear_key_cache()
        self._tmp.cleanup()

    def refresh_via_cookie(self, raw_token):
        self.client.cookies["refresh_token"] = raw_token
        return self.client.post(self.url, {}, content_type="application/json")

    def refresh_via_bearer(self, raw_token):
        return self.client.post(
            self.url,
            {},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

    # ------------------------------------------------------------------
    # Missing token
    # ------------------------------------------------------------------

    def test_requires_refresh_token(self):
        response = self.client.post(self.url, {}, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Success
    # ------------------------------------------------------------------

    def test_successful_refresh_via_cookie(self):
        response = self.refresh_via_cookie(self.tokens.refresh_token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["msg"], "Token refreshed.")

    def test_successful_refresh_via_bearer_header(self):
        response = self.refresh_via_bearer(self.tokens.refresh_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_successful_refresh_sets_new_cookies(self):
        response = self.refresh_via_cookie(self.tokens.refresh_token)

        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        self.assertNotEqual(
            response.cookies["access_token"].value, self.tokens.access_token
        )
        self.assertNotEqual(
            response.cookies["refresh_token"].value, self.tokens.refresh_token
        )

    def test_successful_refresh_keeps_same_session(self):
        self.assertEqual(Session.objects.count(), 1)

        self.refresh_via_cookie(self.tokens.refresh_token)

        self.assertEqual(Session.objects.count(), 1)  # no new session created

    def test_mobile_client_gets_raw_tokens_in_body(self):
        self.client.cookies["refresh_token"] = self.tokens.refresh_token
        response = self.client.post(
            self.url,
            {},
            content_type="application/json",
            HTTP_X_CLIENT_TYPE="mobile",
        )
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)

    # ------------------------------------------------------------------
    # Failure cases
    # ------------------------------------------------------------------

    def test_garbage_token_rejected(self):
        response = self.refresh_via_cookie("not-a-real-jwt")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["msg"], "Invalid or expired session. Please log in again."
        )

    def test_access_token_used_as_refresh_token_rejected(self):
        response = self.refresh_via_cookie(self.tokens.access_token)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_refresh_token_rejected(self):
        expired_token, _, _ = encode_token(
            account_id=self.account.pk,
            session_id=self.tokens.session_id,
            token_type="refresh",
            lifetime=timedelta(seconds=-1),
        )
        response = self.refresh_via_cookie(expired_token)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_revoked_session_rejected(self):
        Session.objects.get(pk=self.tokens.session_id).revoke()

        response = self.refresh_via_cookie(self.tokens.refresh_token)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_failed_refresh_clears_cookies(self):
        response = self.refresh_via_cookie("not-a-real-jwt")

        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")

    # ------------------------------------------------------------------
    # Reuse detection — the important one
    # ------------------------------------------------------------------

    def test_reusing_a_rotated_refresh_token_is_rejected_and_revokes_session(self):
        first_response = self.refresh_via_cookie(self.tokens.refresh_token)
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)

        # Replay the ORIGINAL token, now superseded by the rotation above.
        replay_response = self.refresh_via_cookie(self.tokens.refresh_token)

        self.assertEqual(replay_response.status_code, status.HTTP_401_UNAUTHORIZED)

        session = Session.objects.get(pk=self.tokens.session_id)
        self.assertTrue(session.is_revoked)

    def test_after_reuse_detection_the_rotated_token_also_stops_working(self):
        """
        Once reuse triggers revocation, even the legitimately rotated
        token from the first refresh should stop working too — the
        whole session is dead, not just the replayed token.
        """
        first_response = self.refresh_via_cookie(self.tokens.refresh_token)
        new_refresh_token = first_response.cookies["refresh_token"].value

        self.refresh_via_cookie(self.tokens.refresh_token)  # triggers revocation

        second_attempt = self.refresh_via_cookie(new_refresh_token)
        self.assertEqual(second_attempt.status_code, status.HTTP_401_UNAUTHORIZED)
