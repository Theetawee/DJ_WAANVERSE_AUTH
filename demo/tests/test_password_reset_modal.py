# tests/test_password_reset_code_model.py
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dj_waanverse_auth.models import PasswordResetCode, MAX_ATTEMPTS

Account = get_user_model()


class PasswordResetCodeModelTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
            is_active=True,
        )

    def test_issue_for_creates_row_and_returns_raw_values(self):
        instance, code, token = PasswordResetCode.issue_for(self.account)

        self.assertEqual(instance.account_id, self.account.pk)
        self.assertTrue(code.isdigit())
        self.assertEqual(len(code), 6)
        self.assertGreater(len(token), 20)

    def test_raw_code_and_token_not_stored(self):
        instance, code, token = PasswordResetCode.issue_for(self.account)
        self.assertNotEqual(instance.code_hash, code)
        self.assertNotEqual(instance.token_hash, token)

    def test_matches_correct_code_not_wrong_one(self):
        instance, code, _ = PasswordResetCode.issue_for(self.account)
        self.assertTrue(instance.matches(code, is_code=True))
        self.assertFalse(instance.matches("000000", is_code=True))

    def test_matches_correct_token_not_wrong_one(self):
        instance, _, token = PasswordResetCode.issue_for(self.account)
        self.assertTrue(instance.matches(token, is_code=False))
        self.assertFalse(instance.matches("wrong-token", is_code=False))

    def test_code_and_token_are_not_interchangeable(self):
        instance, code, token = PasswordResetCode.issue_for(self.account)
        self.assertFalse(instance.matches(code, is_code=False))
        self.assertFalse(instance.matches(token, is_code=True))

    def test_is_valid_for_true_when_fresh(self):
        instance, _, _ = PasswordResetCode.issue_for(self.account)
        self.assertTrue(instance.is_valid_for(is_code=True))
        self.assertTrue(instance.is_valid_for(is_code=False))

    def test_is_valid_for_false_when_used(self):
        instance, _, _ = PasswordResetCode.issue_for(self.account)
        instance.is_used = True
        instance.save(update_fields=["is_used"])
        self.assertFalse(instance.is_valid_for(is_code=True))

    def test_is_valid_for_false_when_attempts_exhausted(self):
        instance, _, _ = PasswordResetCode.issue_for(self.account)
        instance.attempts = MAX_ATTEMPTS
        instance.save(update_fields=["attempts"])
        self.assertFalse(instance.is_valid_for(is_code=True))

    def test_code_and_link_expiries_are_independent(self):
        instance, _, _ = PasswordResetCode.issue_for(self.account)
        instance.code_expires_at = timezone.now() - timezone.timedelta(seconds=1)
        instance.save(update_fields=["code_expires_at"])

        self.assertFalse(instance.is_valid_for(is_code=True))
        self.assertTrue(instance.is_valid_for(is_code=False))

    def test_issuing_again_invalidates_previous_unused_code(self):
        first, _, _ = PasswordResetCode.issue_for(self.account)
        second, _, _ = PasswordResetCode.issue_for(self.account)

        first.refresh_from_db()
        self.assertTrue(first.is_used)
        self.assertFalse(second.is_used)

    def test_reset_code_and_verification_code_are_independent_tables(self):
        """
        Issuing a password reset code must NOT invalidate a pending
        signup-verification code for the same account, and vice
        versa — they share issue_for's shape but not its scope.
        """
        from dj_waanverse_auth.models import VerificationCode

        verification, verification_code, _ = VerificationCode.issue_for(self.account)
        reset, reset_code, _ = PasswordResetCode.issue_for(self.account)

        verification.refresh_from_db()
        reset.refresh_from_db()

        self.assertFalse(verification.is_used)
        self.assertFalse(reset.is_used)
        self.assertNotEqual(verification_code, reset_code)
