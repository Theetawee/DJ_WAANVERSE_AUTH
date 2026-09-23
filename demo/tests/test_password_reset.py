# tests/test_password_reset_views.py
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from dj_waanverse_auth.models import PasswordResetCode, Session
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache
from tests.utils import generate_rsa_keypair_files

Account = get_user_model()
KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"
VIEW_MODULE = "dj_waanverse_auth.views.password_reset_views"


class PasswordResetRequestViewTests(TestCase):
    def setUp(self):
        self.url = reverse("dj_waanverse_auth_password_reset_request")
        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
            is_active=True,
        )

    def request_reset(self, identifier, delivery=None):
        payload = {"identifier": identifier}
        if delivery is not None:
            payload["delivery"] = delivery
        return self.client.post(self.url, payload, content_type="application/json")

    # ------------------------------------------------------------------
    # Basic validation
    # ------------------------------------------------------------------

    def test_requires_identifier(self):
        response = self.client.post(self.url, {}, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_invalid_delivery_value(self):
        response = self.request_reset("wave@example.com", delivery="carrier-pigeon")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_unrecognized_identifier(self):
        response = self.request_reset("not-an-email-or-phone")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_link_delivery_for_phone(self):
        response = self.request_reset("+256700123456", delivery="link")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Enumeration resistance
    # ------------------------------------------------------------------

    @patch(f"{VIEW_MODULE}.send_verification_code_email")
    def test_nonexistent_account_returns_generic_success(self, mock_send):
        response = self.request_reset("nobody@example.com")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_not_called()
        self.assertEqual(PasswordResetCode.objects.count(), 0)

    @patch(f"{VIEW_MODULE}.send_verification_code_email")
    def test_unverified_account_returns_generic_success_and_sends_nothing(
        self, mock_send
    ):
        Account.objects.create_user(
            email_address="pending@example.com",
            password="StrongPassword123!",
            is_active=False,
        )
        response = self.request_reset("pending@example.com")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_not_called()
        self.assertEqual(PasswordResetCode.objects.count(), 0)

    def test_response_identical_for_missing_and_unverified_accounts(self):
        Account.objects.create_user(
            email_address="pending@example.com",
            password="StrongPassword123!",
            is_active=False,
        )
        missing = self.request_reset("nobody@example.com")
        unverified = self.request_reset("pending@example.com")
        self.assertEqual(missing.data["msg"], unverified.data["msg"])

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------

    @patch(f"{VIEW_MODULE}.send_verification_code_email")
    def test_email_code_delivery_issues_code_and_calls_sender(self, mock_send):
        response = self.request_reset("wave@example.com", delivery="code")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            PasswordResetCode.objects.filter(account=self.account).count(), 1
        )
        mock_send.assert_called_once()

    @patch(f"{VIEW_MODULE}.send_verification_link_email")
    @patch(f"{VIEW_MODULE}.send_verification_code_email")
    def test_email_link_delivery_calls_link_sender_not_code_sender(
        self, mock_code, mock_link
    ):
        self.request_reset("wave@example.com", delivery="link")
        mock_link.assert_called_once()
        mock_code.assert_not_called()

    @patch(f"{VIEW_MODULE}.send_verification_sms")
    def test_phone_delivery_calls_sms_sender(self, mock_send):
        Account.objects.create_user(
            email_address=None,
            phone_number="+256700123456",
            phone_region="UG",
            password="StrongPassword123!",
            is_active=True,
        )
        response = self.request_reset("+256700123456")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called_once()

    @patch(f"{VIEW_MODULE}.send_verification_code_email", side_effect=Exception("boom"))
    def test_sender_exception_does_not_surface_as_500(self, mock_send):
        response = self.request_reset("wave@example.com")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called_once()

    @patch(f"{VIEW_MODULE}.send_verification_code_email")
    def test_reissuing_invalidates_previous_code(self, mock_send):
        self.request_reset("wave@example.com")
        first = PasswordResetCode.objects.get(account=self.account, is_used=False)

        self.request_reset("wave@example.com")

        first.refresh_from_db()
        self.assertTrue(first.is_used)
        self.assertEqual(
            PasswordResetCode.objects.filter(
                account=self.account, is_used=False
            ).count(),
            1,
        )


class PasswordResetConfirmViewTests(TestCase):
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

        self.url = reverse("dj_waanverse_auth_password_reset_confirm")
        self.old_password = "OldPassword123!"
        self.new_password = "NewStrongPassword456!"
        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password=self.old_password,
            is_active=True,
        )
        self.reset, self.code, self.token = PasswordResetCode.issue_for(self.account)

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        clear_key_cache()
        self._tmp.cleanup()

    def confirm(self, identifier, access, new_password=None, mobile=False):
        headers = {"HTTP_X_CLIENT_TYPE": "mobile"} if mobile else {}
        return self.client.post(
            self.url,
            {
                "identifier": identifier,
                "access": access,
                "new_password": (
                    new_password if new_password is not None else self.new_password
                ),
            },
            content_type="application/json",
            **headers,
        )

    # ------------------------------------------------------------------
    # Basic validation
    # ------------------------------------------------------------------

    def test_requires_identifier(self):
        response = self.client.post(
            self.url,
            {"access": self.code, "new_password": self.new_password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_access(self):
        response = self.client.post(
            self.url,
            {"identifier": "wave@example.com", "new_password": self.new_password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_new_password(self):
        response = self.client.post(
            self.url,
            {"identifier": "wave@example.com", "access": self.code},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_overlong_password(self):
        response = self.confirm("wave@example.com", self.code, new_password="a" * 200)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_weak_new_password(self):
        response = self.confirm("wave@example.com", self.code, new_password="12345678")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.account.refresh_from_db()
        self.assertTrue(self.account.check_password(self.old_password))  # unchanged

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_correct_code_resets_password(self):
        response = self.confirm("wave@example.com", self.code)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.account.refresh_from_db()
        self.assertTrue(self.account.check_password(self.new_password))
        self.assertFalse(self.account.check_password(self.old_password))

    def test_correct_link_token_resets_password(self):
        response = self.confirm("wave@example.com", self.token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.account.refresh_from_db()
        self.assertTrue(self.account.check_password(self.new_password))

    def test_successful_reset_marks_code_used(self):
        self.confirm("wave@example.com", self.code)
        self.reset.refresh_from_db()
        self.assertTrue(self.reset.is_used)

    def test_successful_reset_issues_tokens_and_cookies(self):
        response = self.confirm("wave@example.com", self.code)

        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        self.assertTrue(response.cookies["access_token"]["httponly"])

    def test_mobile_client_gets_raw_tokens_in_body(self):
        response = self.confirm("wave@example.com", self.code, mobile=True)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)

    def test_web_client_body_excludes_raw_tokens(self):
        response = self.confirm("wave@example.com", self.code)
        self.assertNotIn("access_token", response.data)

    # ------------------------------------------------------------------
    # Session revocation — the security-relevant part
    # ------------------------------------------------------------------

    def test_existing_sessions_revoked_on_reset(self):
        old_session = Session.objects.create(account=self.account)
        old_session.set_refresh_token("some-old-refresh-token")
        old_session.save()

        self.confirm("wave@example.com", self.code)

        old_session.refresh_from_db()
        self.assertTrue(old_session.is_revoked)

    def test_already_revoked_sessions_left_alone(self):
        already_revoked = Session.objects.create(account=self.account)
        already_revoked.revoke()
        original_revoked_at = already_revoked.revoked_at

        self.confirm("wave@example.com", self.code)

        already_revoked.refresh_from_db()
        self.assertEqual(already_revoked.revoked_at, original_revoked_at)

    def test_other_accounts_sessions_untouched(self):
        other_account = Account.objects.create_user(
            email_address="other@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        other_session = Session.objects.create(account=other_account)

        self.confirm("wave@example.com", self.code)

        other_session.refresh_from_db()
        self.assertFalse(other_session.is_revoked)

    def test_new_session_from_this_reset_is_not_itself_revoked(self):
        self.confirm("wave@example.com", self.code)

        # exactly one session should exist: the one issue_tokens_for_account
        # just created, and it must NOT have been caught by the revoke-all
        # update that ran moments before it (ordering matters here).
        sessions = Session.objects.filter(account=self.account)
        self.assertEqual(sessions.count(), 1)
        self.assertFalse(sessions.first().is_revoked)

    # ------------------------------------------------------------------
    # MAX_ATTEMPTS / expiry / reuse — same shape as verification
    # ------------------------------------------------------------------

    def test_wrong_code_increments_attempts(self):
        self.confirm("wave@example.com", "000000")
        self.reset.refresh_from_db()
        self.assertEqual(self.reset.attempts, 1)

    def test_exceeding_max_attempts_locks_out_even_correct_code(self):
        from dj_waanverse_auth.models import MAX_ATTEMPTS

        for _ in range(MAX_ATTEMPTS):
            self.confirm("wave@example.com", "000000")

        response = self.confirm("wave@example.com", self.code)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.account.refresh_from_db()
        self.assertTrue(self.account.check_password(self.old_password))  # unchanged

    def test_expired_code_rejected(self):
        self.reset.code_expires_at = timezone.now() - timezone.timedelta(seconds=1)
        self.reset.save(update_fields=["code_expires_at"])

        response = self.confirm("wave@example.com", self.code)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_already_used_code_cannot_be_reused(self):
        self.confirm("wave@example.com", self.code)

        second_attempt = self.confirm(
            "wave@example.com", self.code, new_password="AnotherPassword789!"
        )
        self.assertEqual(second_attempt.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Identifier / account state edge cases
    # ------------------------------------------------------------------

    def test_phone_rejects_link_shaped_access(self):
        phone_account = Account.objects.create_user(
            email_address=None,
            phone_number="+256700123456",
            phone_region="UG",
            password="StrongPassword123!",
            is_active=True,
        )
        _, phone_code, phone_token = PasswordResetCode.issue_for(phone_account)

        response = self.confirm("+256700123456", phone_token)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_account_returns_generic_error(self):
        response = self.confirm("nobody@example.com", "123456")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unverified_account_rejected(self):
        Account.objects.create_user(
            email_address="pending@example.com",
            password="StrongPassword123!",
            is_active=False,
        )
        response = self.confirm("pending@example.com", self.code)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
