# tests/test_logout_view.py
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
from dj_waanverse_auth.utils.security.jwt import ACCESS, encode_token
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache
from dj_waanverse_auth.utils.security.tokens import issue_tokens_for_account
from tests.utils import generate_rsa_keypair_files

Account = get_user_model()
KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"
CSRF_TOKEN = "test-csrf-token"


class LogoutViewTests(TestCase):
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

        self.url = reverse("dj_waanverse_auth_logout")
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

    def logout_via_cookie(self, refresh_token, access_token=None, with_csrf=True):
        if refresh_token is not None:
            self.client.cookies["refresh_token"] = refresh_token
        if access_token is not None:
            self.client.cookies["access_token"] = access_token
        headers = {}
        if with_csrf and refresh_token is not None:
            self.client.cookies[CSRF_COOKIE_NAME] = CSRF_TOKEN
            headers["HTTP_X_CSRF_TOKEN"] = CSRF_TOKEN
        return self.client.post(
            self.url, {}, content_type="application/json", **headers
        )

    def logout_via_bearer(self, refresh_token):
        return self.client.post(
            self.url,
            {},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {refresh_token}",
        )

    # ------------------------------------------------------------------
    # No token at all — still succeeds
    # ------------------------------------------------------------------

    def test_logout_with_no_token_still_returns_200(self):
        response = self.client.post(self.url, {}, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["msg"], "Logged out.")

    def test_logout_with_no_token_does_not_touch_any_session(self):
        self.client.post(self.url, {}, content_type="application/json")
        session = Session.objects.get(pk=self.tokens.session_id)
        self.assertFalse(session.is_revoked)

    # ------------------------------------------------------------------
    # Valid refresh token — actually revokes
    # ------------------------------------------------------------------

    def test_valid_refresh_token_via_cookie_revokes_session(self):
        response = self.logout_via_cookie(self.tokens.refresh_token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session = Session.objects.get(pk=self.tokens.session_id)
        self.assertTrue(session.is_revoked)

    def test_valid_refresh_token_via_bearer_revokes_session(self):
        response = self.logout_via_bearer(self.tokens.refresh_token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session = Session.objects.get(pk=self.tokens.session_id)
        self.assertTrue(session.is_revoked)

    def test_logout_clears_auth_cookies(self):
        response = self.logout_via_cookie(self.tokens.refresh_token)

        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")

    def test_revoked_session_can_no_longer_be_refreshed(self):
        """Confirms logout has a real downstream effect, not just a flag flip."""
        self.logout_via_cookie(self.tokens.refresh_token)

        from dj_waanverse_auth.utils.security.tokens import (
            RefreshError,
            rotate_refresh_token,
        )

        with self.assertRaises(RefreshError):
            rotate_refresh_token(self.tokens.refresh_token)

    def test_only_the_targeted_session_is_revoked_not_others(self):
        other_tokens = issue_tokens_for_account(self.account, request=None)

        self.logout_via_cookie(self.tokens.refresh_token)

        self.assertTrue(Session.objects.get(pk=self.tokens.session_id).is_revoked)
        self.assertFalse(Session.objects.get(pk=other_tokens.session_id).is_revoked)

    # ------------------------------------------------------------------
    # Works without any valid access token — the whole point
    # ------------------------------------------------------------------

    def test_logout_succeeds_with_expired_access_token_present(self):
        expired_access, _, _ = encode_token(
            account_id=self.account.pk,
            session_id=self.tokens.session_id,
            token_type=ACCESS,
            lifetime=timedelta(seconds=-1),
        )
        response = self.logout_via_cookie(
            self.tokens.refresh_token, access_token=expired_access
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Session.objects.get(pk=self.tokens.session_id).is_revoked)

    def test_logout_succeeds_with_garbage_access_token_present(self):
        response = self.logout_via_cookie(
            self.tokens.refresh_token, access_token="not-a-real-jwt"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_never_requires_authentication(self):
        """No Authorization header, no access_token cookie, at all — still 200."""
        response = self.client.post(self.url, {}, content_type="application/json")
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # Invalid / already-dead refresh tokens — always still 200
    # ------------------------------------------------------------------

    def test_garbage_refresh_token_still_returns_200(self):
        response = self.logout_via_cookie("not-a-real-jwt")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_expired_refresh_token_still_returns_200(self):
        expired_refresh, _, _ = encode_token(
            account_id=self.account.pk,
            session_id=self.tokens.session_id,
            token_type="refresh",
            lifetime=timedelta(seconds=-1),
        )
        response = self.logout_via_cookie(expired_refresh)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_access_token_used_as_refresh_token_still_returns_200_but_does_not_revoke(
        self,
    ):
        response = self.logout_via_cookie(self.tokens.access_token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session = Session.objects.get(pk=self.tokens.session_id)
        self.assertFalse(
            session.is_revoked
        )  # wrong token type never matches -> nothing to revoke

    def test_token_for_nonexistent_session_still_returns_200(self):
        Session.objects.filter(pk=self.tokens.session_id).delete()
        response = self.logout_via_cookie(self.tokens.refresh_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superseded_rotated_token_does_not_revoke_the_new_one(self):
        from dj_waanverse_auth.utils.security.tokens import rotate_refresh_token

        old_refresh_token = self.tokens.refresh_token
        rotate_refresh_token(old_refresh_token)  # legitimate rotation, once

        response = self.logout_via_cookie(
            old_refresh_token
        )  # present the now-superseded token
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        session = Session.objects.get(pk=self.tokens.session_id)
        self.assertFalse(session.is_revoked)  # logout must not force-match a stale hash

        def test_logging_out_an_already_revoked_session_is_a_harmless_noop(self):
            Session.objects.get(pk=self.tokens.session_id).revoke()

            response = self.logout_via_cookie(self.tokens.refresh_token)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # CSRF — cookie path only
    # ------------------------------------------------------------------

    def test_cookie_logout_without_csrf_header_is_rejected(self):
        response = self.logout_via_cookie(self.tokens.refresh_token, with_csrf=False)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cookie_logout_csrf_rejection_does_not_revoke_session(self):
        self.logout_via_cookie(self.tokens.refresh_token, with_csrf=False)
        session = Session.objects.get(pk=self.tokens.session_id)
        self.assertFalse(session.is_revoked)

    def test_bearer_logout_never_requires_csrf(self):
        response = self.logout_via_bearer(self.tokens.refresh_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
