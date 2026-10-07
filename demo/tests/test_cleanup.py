from __future__ import annotations

from datetime import timedelta
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from dj_waanverse_auth.models import (
    PasswordResetCode,
    Session,
    VerificationCode,
)

User = get_user_model()


class CleanupSessionsCommandTests(TestCase):
    def setUp(self):
        self.account = User.objects.create_user(
            email_address="sessions@example.com",
            password="test-password",
        )

    def create_session(self, **kwargs):
        defaults = {
            "account": self.account,
            "refresh_token_hash": "a" * 64,
        }
        defaults.update(kwargs)
        return Session.objects.create(**defaults)

    def run_command(self, *args, **kwargs):
        output = StringIO()

        call_command(
            "cleanup_sessions",
            *args,
            stdout=output,
            **kwargs,
        )

        return output.getvalue()

    def test_deletes_revoked_sessions(self):
        session = self.create_session(
            is_revoked=True,
            revoked_at=timezone.now(),
        )

        self.run_command()

        self.assertFalse(Session.objects.filter(pk=session.pk).exists())

    def test_deletes_inactive_sessions(self):
        session = self.create_session()
        session.last_used_at = timezone.now() - timedelta(days=31)
        session.save(update_fields=["last_used_at"])

        session.refresh_from_db()

        self.run_command()

        self.assertFalse(Session.objects.filter(pk=session.pk).exists())

    def test_keeps_recent_sessions(self):
        session = self.create_session(
            last_used_at=timezone.now() - timedelta(days=10),
        )

        self.run_command()

        self.assertTrue(Session.objects.filter(pk=session.pk).exists())

    def test_keeps_active_sessions_even_if_created_long_ago(self):
        session = self.create_session(
            created_at=timezone.now() - timedelta(days=90),
            last_used_at=timezone.now() - timedelta(days=2),
        )

        self.run_command()

        self.assertTrue(Session.objects.filter(pk=session.pk).exists())

    def test_custom_inactive_days(self):
        session = self.create_session()

        session.last_used_at = timezone.now() - timedelta(days=61)
        session.save(update_fields=["last_used_at"])
        session.refresh_from_db()

        self.run_command("--inactive-days", "60")

        self.assertFalse(Session.objects.filter(pk=session.pk).exists())

    def test_custom_inactive_days_keeps_newer_session(self):
        session = self.create_session(
            last_used_at=timezone.now() - timedelta(days=59),
        )

        self.run_command("--inactive-days", "60")

        self.assertTrue(Session.objects.filter(pk=session.pk).exists())

    def test_dry_run_does_not_delete_revoked_sessions(self):
        session = self.create_session(
            is_revoked=True,
            revoked_at=timezone.now(),
        )

        output = self.run_command("--dry-run")

        self.assertTrue(Session.objects.filter(pk=session.pk).exists())

        self.assertIn("Dry run", output)

    def test_dry_run_does_not_delete_inactive_sessions(self):
        session = self.create_session(
            last_used_at=timezone.now() - timedelta(days=31),
        )

        output = self.run_command("--dry-run")

        self.assertTrue(Session.objects.filter(pk=session.pk).exists())

        self.assertIn("Dry run", output)

    def test_invalid_inactive_days_is_rejected(self):
        output = StringIO()
        error_output = StringIO()

        call_command(
            "cleanup_sessions",
            "--inactive-days",
            "0",
            stdout=output,
            stderr=error_output,
        )

        self.assertIn(
            "--inactive-days must be at least 1.",
            error_output.getvalue(),
        )

    @override_settings(refresh_token_lifetime=timedelta(days=30))
    def test_uses_refresh_token_lifetime_when_inactive_days_is_none(self):
        old_session = self.create_session()
        recent_session = self.create_session()

        Session.objects.filter(pk=old_session.pk).update(
            last_used_at=timezone.now() - timedelta(days=31)
        )

        Session.objects.filter(pk=recent_session.pk).update(
            last_used_at=timezone.now() - timedelta(days=29)
        )

        self.run_command()

        self.assertFalse(Session.objects.filter(pk=old_session.pk).exists())
        self.assertTrue(Session.objects.filter(pk=recent_session.pk).exists())


class CleanupVerificationCodesCommandTests(TestCase):
    def setUp(self):
        self.account = User.objects.create_user(
            email_address="verification@example.com",
            password="test-password",
        )

    def create_code(self, **kwargs):
        now = timezone.now()

        defaults = {
            "account": self.account,
            "code_hash": "a" * 64,
            "token_hash": "b" * 64,
            "code_expires_at": now + timedelta(minutes=10),
            "link_expires_at": now + timedelta(minutes=10),
        }

        defaults.update(kwargs)

        return VerificationCode.objects.create(**defaults)

    def run_command(self, *args, **kwargs):
        output = StringIO()

        call_command(
            "cleanup_verification_codes",
            *args,
            stdout=output,
            **kwargs,
        )

        return output.getvalue()

    def test_deletes_used_verification_codes(self):
        code = self.create_code(
            is_used=True,
        )

        self.run_command()

        self.assertFalse(VerificationCode.objects.filter(pk=code.pk).exists())

    def test_deletes_fully_expired_verification_codes(self):
        now = timezone.now()

        code = self.create_code(
            code_expires_at=now - timedelta(minutes=10),
            link_expires_at=now - timedelta(minutes=10),
        )

        self.run_command()

        self.assertFalse(VerificationCode.objects.filter(pk=code.pk).exists())

    def test_keeps_code_when_numeric_code_is_expired_but_link_is_valid(self):
        now = timezone.now()

        code = self.create_code(
            code_expires_at=now - timedelta(minutes=10),
            link_expires_at=now + timedelta(minutes=10),
        )

        self.run_command()

        self.assertTrue(VerificationCode.objects.filter(pk=code.pk).exists())

    def test_keeps_code_when_link_is_expired_but_numeric_code_is_valid(self):
        now = timezone.now()

        code = self.create_code(
            code_expires_at=now + timedelta(minutes=10),
            link_expires_at=now - timedelta(minutes=10),
        )

        self.run_command()

        self.assertTrue(VerificationCode.objects.filter(pk=code.pk).exists())

    def test_keeps_valid_unused_verification_codes(self):
        code = self.create_code()

        self.run_command()

        self.assertTrue(VerificationCode.objects.filter(pk=code.pk).exists())

    def test_dry_run_does_not_delete_used_codes(self):
        code = self.create_code(
            is_used=True,
        )

        output = self.run_command("--dry-run")

        self.assertTrue(VerificationCode.objects.filter(pk=code.pk).exists())

        self.assertIn("Dry run", output)

    def test_dry_run_does_not_delete_expired_codes(self):
        now = timezone.now()

        code = self.create_code(
            code_expires_at=now - timedelta(minutes=10),
            link_expires_at=now - timedelta(minutes=10),
        )

        output = self.run_command("--dry-run")

        self.assertTrue(VerificationCode.objects.filter(pk=code.pk).exists())

        self.assertIn("Dry run", output)

    def test_deletes_multiple_eligible_records(self):
        now = timezone.now()

        used_code = self.create_code(
            is_used=True,
        )

        expired_code = self.create_code(
            code_expires_at=now - timedelta(minutes=10),
            link_expires_at=now - timedelta(minutes=10),
        )

        valid_code = self.create_code()

        self.run_command()

        self.assertFalse(VerificationCode.objects.filter(pk=used_code.pk).exists())

        self.assertFalse(VerificationCode.objects.filter(pk=expired_code.pk).exists())

        self.assertTrue(VerificationCode.objects.filter(pk=valid_code.pk).exists())


class CleanupPasswordResetCodesCommandTests(TestCase):
    def setUp(self):
        self.account = User.objects.create_user(
            email_address="password-reset@example.com",
            password="test-password",
        )

    def create_code(self, **kwargs):
        now = timezone.now()

        defaults = {
            "account": self.account,
            "code_hash": "a" * 64,
            "token_hash": "b" * 64,
            "code_expires_at": now + timedelta(minutes=10),
            "link_expires_at": now + timedelta(minutes=10),
        }

        defaults.update(kwargs)

        return PasswordResetCode.objects.create(**defaults)

    def run_command(self, *args, **kwargs):
        output = StringIO()
        call_command(
            "cleanup_password_reset_codes",
            *args,
            stdout=output,
            **kwargs,
        )

        return output.getvalue()

    def test_deletes_used_password_reset_codes(self):
        code = self.create_code(
            is_used=True,
        )

        self.run_command()

        self.assertFalse(PasswordResetCode.objects.filter(pk=code.pk).exists())

    def test_deletes_fully_expired_password_reset_codes(self):
        now = timezone.now()

        code = self.create_code(
            code_expires_at=now - timedelta(minutes=10),
            link_expires_at=now - timedelta(minutes=10),
        )

        self.run_command()

        self.assertFalse(PasswordResetCode.objects.filter(pk=code.pk).exists())

    def test_keeps_code_when_numeric_code_is_expired_but_link_is_valid(self):
        now = timezone.now()

        code = self.create_code(
            code_expires_at=now - timedelta(minutes=10),
            link_expires_at=now + timedelta(minutes=10),
        )

        self.run_command()

        self.assertTrue(PasswordResetCode.objects.filter(pk=code.pk).exists())

    def test_keeps_code_when_link_is_expired_but_numeric_code_is_valid(self):
        now = timezone.now()

        code = self.create_code(
            code_expires_at=now + timedelta(minutes=10),
            link_expires_at=now - timedelta(minutes=10),
        )

        self.run_command()

        self.assertTrue(PasswordResetCode.objects.filter(pk=code.pk).exists())

    def test_keeps_valid_unused_password_reset_codes(self):
        code = self.create_code()

        self.run_command()

        self.assertTrue(PasswordResetCode.objects.filter(pk=code.pk).exists())

    def test_dry_run_does_not_delete_used_codes(self):
        code = self.create_code(
            is_used=True,
        )

        output = self.run_command("--dry-run")

        self.assertTrue(PasswordResetCode.objects.filter(pk=code.pk).exists())

        self.assertIn("Dry run", output)

    def test_dry_run_does_not_delete_expired_codes(self):
        now = timezone.now()

        code = self.create_code(
            code_expires_at=now - timedelta(minutes=10),
            link_expires_at=now - timedelta(minutes=10),
        )

        output = self.run_command("--dry-run")

        self.assertTrue(PasswordResetCode.objects.filter(pk=code.pk).exists())

        self.assertIn("Dry run", output)

    def test_deletes_multiple_eligible_records(self):
        now = timezone.now()

        used_code = self.create_code(
            is_used=True,
        )

        expired_code = self.create_code(
            code_expires_at=now - timedelta(minutes=10),
            link_expires_at=now - timedelta(minutes=10),
        )

        valid_code = self.create_code()

        self.run_command()

        self.assertFalse(PasswordResetCode.objects.filter(pk=used_code.pk).exists())

        self.assertFalse(PasswordResetCode.objects.filter(pk=expired_code.pk).exists())

        self.assertTrue(PasswordResetCode.objects.filter(pk=valid_code.pk).exists())


class CleanupAuthCommandTests(TestCase):
    def setUp(self):
        self.account = User.objects.create_user(
            email_address="cleanup-auth@example.com",
            password="test-password",
        )

    def run_command(self, *args, **kwargs):
        output = StringIO()
        call_command(
            "cleanup_auth",
            *args,
            stdout=output,
            **kwargs,
        )

        return output.getvalue()

    def test_runs_all_cleanup_commands(self):
        now = timezone.now()

        revoked_session = Session.objects.create(
            account=self.account,
            refresh_token_hash="a" * 64,
            is_revoked=True,
            revoked_at=now,
        )

        expired_verification = VerificationCode.objects.create(
            account=self.account,
            code_hash="b" * 64,
            token_hash="c" * 64,
            code_expires_at=now - timedelta(minutes=10),
            link_expires_at=now - timedelta(minutes=10),
        )

        expired_password_reset = PasswordResetCode.objects.create(
            account=self.account,
            code_hash="d" * 64,
            token_hash="e" * 64,
            code_expires_at=now - timedelta(minutes=10),
            link_expires_at=now - timedelta(minutes=10),
        )

        self.run_command()

        self.assertFalse(Session.objects.filter(pk=revoked_session.pk).exists())

        self.assertFalse(
            VerificationCode.objects.filter(pk=expired_verification.pk).exists()
        )

        self.assertFalse(
            PasswordResetCode.objects.filter(pk=expired_password_reset.pk).exists()
        )

    def test_dry_run_keeps_all_records(self):
        now = timezone.now()

        revoked_session = Session.objects.create(
            account=self.account,
            refresh_token_hash="a" * 64,
            is_revoked=True,
            revoked_at=now,
        )

        expired_verification = VerificationCode.objects.create(
            account=self.account,
            code_hash="b" * 64,
            token_hash="c" * 64,
            code_expires_at=now - timedelta(minutes=10),
            link_expires_at=now - timedelta(minutes=10),
        )

        expired_password_reset = PasswordResetCode.objects.create(
            account=self.account,
            code_hash="d" * 64,
            token_hash="e" * 64,
            code_expires_at=now - timedelta(minutes=10),
            link_expires_at=now - timedelta(minutes=10),
        )

        output = self.run_command("--dry-run")

        self.assertTrue(Session.objects.filter(pk=revoked_session.pk).exists())

        self.assertTrue(
            VerificationCode.objects.filter(pk=expired_verification.pk).exists()
        )

        self.assertTrue(
            PasswordResetCode.objects.filter(pk=expired_password_reset.pk).exists()
        )

        self.assertIn("Dry run", output)

    def test_passes_inactive_days_to_session_cleanup(self):
        session = Session.objects.create(
            account=self.account,
            refresh_token_hash="a" * 64,
        )
        session.last_used_at = timezone.now() - timedelta(days=61)
        session.save(update_fields=["last_used_at"])
        session.refresh_from_db()

        self.run_command("--inactive-days", "60")

        self.assertFalse(Session.objects.filter(pk=session.pk).exists())

    def test_keeps_recent_session_with_custom_inactive_days(self):
        session = Session.objects.create(
            account=self.account,
            refresh_token_hash="a" * 64,
            last_used_at=timezone.now() - timedelta(days=59),
        )

        self.run_command("--inactive-days", "60")

        self.assertTrue(Session.objects.filter(pk=session.pk).exists())

    def test_keeps_valid_records(self):
        now = timezone.now()

        session = Session.objects.create(
            account=self.account,
            refresh_token_hash="a" * 64,
            last_used_at=now - timedelta(days=2),
        )

        verification = VerificationCode.objects.create(
            account=self.account,
            code_hash="b" * 64,
            token_hash="c" * 64,
            code_expires_at=now + timedelta(minutes=10),
            link_expires_at=now + timedelta(minutes=10),
        )

        password_reset = PasswordResetCode.objects.create(
            account=self.account,
            code_hash="d" * 64,
            token_hash="e" * 64,
            code_expires_at=now + timedelta(minutes=10),
            link_expires_at=now + timedelta(minutes=10),
        )

        self.run_command()

        self.assertTrue(Session.objects.filter(pk=session.pk).exists())

        self.assertTrue(VerificationCode.objects.filter(pk=verification.pk).exists())

        self.assertTrue(PasswordResetCode.objects.filter(pk=password_reset.pk).exists())
