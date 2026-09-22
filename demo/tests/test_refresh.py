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
from dj_waanverse_auth.utils.security.csrf import CSRF_COOKIE_NAME
from dj_waanverse_auth.utils.security.jwt import encode_token
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache
from dj_waanverse_auth.utils.security.tokens import issue_tokens_for_account
from tests.utils import generate_rsa_keypair_files

Account = get_user_model()
KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"
CSRF_TOKEN = "test-csrf-token-value"


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

    def refresh_via_cookie(self, raw_token, with_csrf=True):
        self.client.cookies["refresh_token"] = raw_token
        headers = {}
        if with_csrf:
            self.client.cookies[CSRF_COOKIE_NAME] = CSRF_TOKEN
            headers["HTTP_X_CSRF_TOKEN"] = CSRF_TOKEN
        return self.client.post(
            self.url, {}, content_type="application/json", **headers
        )

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
    # Success — cookie source, with valid CSRF
    # ------------------------------------------------------------------

    def test_successful_refresh_via_cookie_with_valid_csrf(self):
        response = self.refresh_via_cookie(self.tokens.refresh_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["msg"], "Token refreshed.")

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

    def test_successful_refresh_reissues_csrf_cookie_too(self):
        response = self.refresh_via_cookie(self.tokens.refresh_token)
        self.assertIn(CSRF_COOKIE_NAME, response.cookies)

    def test_successful_refresh_keeps_same_session(self):
        self.assertEqual(Session.objects.count(), 1)
        self.refresh_via_cookie(self.tokens.refresh_token)
        self.assertEqual(Session.objects.count(), 1)

    # ------------------------------------------------------------------
    # CSRF enforcement on the cookie path
    # ------------------------------------------------------------------

    def test_cookie_refresh_without_csrf_header_is_rejected(self):
        response = self.refresh_via_cookie(self.tokens.refresh_token, with_csrf=False)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cookie_refresh_with_mismatched_csrf_is_rejected(self):
        self.client.cookies["refresh_token"] = self.tokens.refresh_token
        self.client.cookies[CSRF_COOKIE_NAME] = "cookie-value"
        response = self.client.post(
            self.url,
            {},
            content_type="application/json",
            HTTP_X_CSRF_TOKEN="different-value",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_csrf_rejection_does_not_rotate_or_touch_session(self):
        """A CSRF-blocked request should never reach rotate_refresh_token at all."""
        session_before = Session.objects.get(
            pk=self.tokens.session_id
        ).refresh_token_hash

        self.refresh_via_cookie(self.tokens.refresh_token, with_csrf=False)

        session_after = Session.objects.get(
            pk=self.tokens.session_id
        ).refresh_token_hash
        self.assertEqual(session_before, session_after)

    # ------------------------------------------------------------------
    # Mobile / Bearer path — CSRF must never apply here
    # ------------------------------------------------------------------

    def test_bearer_refresh_succeeds_with_no_csrf_anything(self):
        response = self.refresh_via_bearer(self.tokens.refresh_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bearer_refresh_succeeds_even_with_stray_csrf_cookie_present(self):
        """
        A leftover CSRF cookie from a previous web session in the
        same browser/client shouldn't matter for a bearer-authenticated
        request — the check only fires for cookie-SOURCED tokens.
        """
        self.client.cookies[CSRF_COOKIE_NAME] = "some-leftover-value"
        response = self.refresh_via_bearer(self.tokens.refresh_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_mobile_client_still_gets_raw_tokens_in_body(self):
        response = self.client.post(
            self.url,
            {},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.tokens.refresh_token}",
            HTTP_X_CLIENT_TYPE="mobile",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)

    # ------------------------------------------------------------------
    # Token validity failures (all require valid CSRF to even reach them)
    # ------------------------------------------------------------------

    def test_garbage_token_rejected(self):
        response = self.refresh_via_cookie("not-a-real-jwt")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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
    # Reuse detection
    # ------------------------------------------------------------------

    def test_reusing_a_rotated_refresh_token_is_rejected_and_revokes_session(self):
        first_response = self.refresh_via_cookie(self.tokens.refresh_token)
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)

        replay_response = self.refresh_via_cookie(self.tokens.refresh_token)
        self.assertEqual(replay_response.status_code, status.HTTP_401_UNAUTHORIZED)

        session = Session.objects.get(pk=self.tokens.session_id)
        self.assertTrue(session.is_revoked)

    def test_after_reuse_detection_the_rotated_token_also_stops_working(self):
        first_response = self.refresh_via_cookie(self.tokens.refresh_token)
        new_refresh_token = first_response.cookies["refresh_token"].value

        self.refresh_via_cookie(self.tokens.refresh_token)  # triggers revocation

        second_attempt = self.refresh_via_cookie(new_refresh_token)
        self.assertEqual(second_attempt.status_code, status.HTTP_401_UNAUTHORIZED)
