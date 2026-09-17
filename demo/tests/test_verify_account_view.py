# tests/test_verify_account_view.py
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from dj_waanverse_auth.models import VerificationCode, Session, MAX_ATTEMPTS
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache
from tests.utils import generate_rsa_keypair_files

Account = get_user_model()
KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"


class VerifyAccountViewTests(TestCase):
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

        self.url = reverse("dj_waanverse_auth_verify_account")
        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
        )
        self.verification, self.code, self.token = VerificationCode.issue_for(
            self.account
        )

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        clear_key_cache()
        self._tmp.cleanup()

    def verify(self, identifier, access, mobile=False):
        headers = {"HTTP_X_CLIENT_TYPE": "mobile"} if mobile else {}
        return self.client.post(
            self.url,
            {"identifier": identifier, "access": access},
            content_type="application/json",
            **headers,
        )

    # ------------------------------------------------------------------
    # Happy paths — now also verifying tokens/cookies/session
    # ------------------------------------------------------------------

    def test_correct_code_verifies_account(self):
        response = self.verify("wave@example.com", self.code)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.account.refresh_from_db()
        self.assertTrue(self.account.is_active)
        self.assertTrue(self.account.email_verified)

        self.verification.refresh_from_db()
        self.assertTrue(self.verification.is_used)

    def test_correct_link_token_verifies_account(self):
        response = self.verify("wave@example.com", self.token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.account.refresh_from_db()
        self.assertTrue(self.account.is_active)

    def test_successful_verify_sets_auth_cookies(self):
        response = self.verify("wave@example.com", self.code)

        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        self.assertTrue(response.cookies["access_token"]["httponly"])
        self.assertTrue(response.cookies["refresh_token"]["httponly"])

    def test_successful_verify_creates_session(self):
        self.assertEqual(Session.objects.count(), 0)

        self.verify("wave@example.com", self.code)

        self.assertEqual(Session.objects.count(), 1)
        session = Session.objects.get()
        self.assertEqual(session.account_id, self.account.pk)

    def test_web_client_response_body_excludes_raw_tokens(self):
        response = self.verify("wave@example.com", self.code)

        self.assertNotIn("access_token", response.data)
        self.assertNotIn("refresh_token", response.data)

    def test_mobile_client_response_body_includes_raw_tokens(self):
        response = self.verify("wave@example.com", self.code, mobile=True)

        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        # still gets cookies too, per build_auth_response's contract
        self.assertIn("access_token", response.cookies)

    def test_failed_verify_does_not_create_session_or_cookies(self):
        response = self.verify("wave@example.com", "000000")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Session.objects.count(), 0)
        self.assertNotIn("access_token", response.cookies)

    # ------------------------------------------------------------------
    # MAX_ATTEMPTS exhaustion
    # ------------------------------------------------------------------

    def test_wrong_code_increments_attempts(self):
        self.verify("wave@example.com", "000000")

        self.verification.refresh_from_db()
        self.assertEqual(self.verification.attempts, 1)

    def test_attempts_below_max_still_allow_correct_code(self):
        for _ in range(MAX_ATTEMPTS - 1):
            self.verify("wave@example.com", "000000")

        response = self.verify("wave@example.com", self.code)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.account.refresh_from_db()
        self.assertTrue(self.account.is_active)

    def test_exceeding_max_attempts_locks_out_even_correct_code(self):
        for _ in range(MAX_ATTEMPTS):
            self.verify("wave@example.com", "000000")

        self.verification.refresh_from_db()
        self.assertEqual(self.verification.attempts, MAX_ATTEMPTS)

        response = self.verify("wave@example.com", self.code)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.account.refresh_from_db()
        self.assertFalse(self.account.is_active)

    def test_exceeding_max_attempts_does_not_keep_incrementing_past_lockout(self):
        for _ in range(MAX_ATTEMPTS + 3):
            self.verify("wave@example.com", "000000")

        self.verification.refresh_from_db()
        self.assertEqual(self.verification.attempts, MAX_ATTEMPTS)

    def test_attempts_not_incremented_when_no_verification_exists(self):
        VerificationCode.objects.all().delete()

        response = self.verify("wave@example.com", "000000")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(VerificationCode.objects.count(), 0)

    # ------------------------------------------------------------------
    # Expiry
    # ------------------------------------------------------------------

    def test_expired_code_rejected(self):
        self.verification.code_expires_at = timezone.now() - timezone.timedelta(
            seconds=1
        )
        self.verification.save(update_fields=["code_expires_at"])

        response = self.verify("wave@example.com", self.code)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_link_rejected_independently_of_code_expiry(self):
        self.verification.code_expires_at = timezone.now() - timezone.timedelta(
            seconds=1
        )
        self.verification.save(update_fields=["code_expires_at"])

        response = self.verify("wave@example.com", self.token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # Reuse
    # ------------------------------------------------------------------

    def test_already_used_code_cannot_be_reused(self):
        self.verify("wave@example.com", self.code)

        response = self.verify("wave@example.com", self.code)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Identifier / access shape mismatches
    # ------------------------------------------------------------------

    def test_phone_rejects_link_shaped_access(self):
        phone_account = Account.objects.create_user(
            email_address=None,
            phone_number="+256700123456",
            phone_region="UG",
            password="StrongPassword123!",
        )
        _, phone_code, phone_token = VerificationCode.issue_for(phone_account)

        response = self.verify("+256700123456", phone_token)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"], "Phone verification requires a code, not a link."
        )

    def test_nonexistent_account_returns_generic_error(self):
        response = self.verify("nobody@example.com", "123456")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_already_active_account_returns_generic_error(self):
        self.account.is_active = True
        self.account.save(update_fields=["is_active"])

        response = self.verify("wave@example.com", self.code)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
