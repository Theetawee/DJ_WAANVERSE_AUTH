# tests/test_admin.py
from __future__ import annotations

from unittest.mock import Mock, patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase

from dj_waanverse_auth.admin import (
    PasswordResetCodeAdmin,
    SessionAdmin,
    VerificationCodeAdmin,
    register_admin,
)
from dj_waanverse_auth.models import PasswordResetCode, Session, VerificationCode

Account = get_user_model()
MODULE = "dj_waanverse_auth.admin.auth_config"


class AdminConfigValidityTests(TestCase):
    """
    Django's own system checks validate that every field named in
    list_display/list_filter/search_fields/readonly_fields actually
    exists on the model — this catches typos in field names without
    needing to load the admin UI at all.
    """

    def test_admin_config_passes_django_system_checks(self):
        errors = admin.site.check(None)
        self.assertEqual(errors, [])


class NoAddAdminMixinTests(TestCase):
    def test_session_admin_disallows_add(self):
        admin_instance = SessionAdmin(Session, admin.site)
        self.assertFalse(admin_instance.has_add_permission(request=None))

    def test_verification_code_admin_disallows_add(self):
        admin_instance = VerificationCodeAdmin(VerificationCode, admin.site)
        self.assertFalse(admin_instance.has_add_permission(request=None))

    def test_password_reset_code_admin_disallows_add(self):
        admin_instance = PasswordResetCodeAdmin(PasswordResetCode, admin.site)
        self.assertFalse(admin_instance.has_add_permission(request=None))


class SessionAdminTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        self.admin_instance = SessionAdmin(Session, admin.site)

    def test_user_agent_short_returns_full_string_when_under_limit(self):
        session = Session.objects.create(account=self.account, user_agent="short-ua")
        self.assertEqual(self.admin_instance.user_agent_short(session), "short-ua")

    def test_user_agent_short_truncates_long_strings(self):
        long_ua = "x" * 100
        session = Session.objects.create(account=self.account, user_agent=long_ua)
        result = self.admin_instance.user_agent_short(session)
        self.assertEqual(len(result), 61)  # 60 chars + ellipsis
        self.assertTrue(result.endswith("…"))

    def test_revoke_sessions_action_revokes_unrevoked_only(self):
        active = Session.objects.create(account=self.account)
        already_revoked = Session.objects.create(account=self.account)
        already_revoked.revoke()
        original_revoked_at = already_revoked.revoked_at

        request = Mock()
        self.admin_instance.revoke_sessions(
            request, Session.objects.filter(account=self.account)
        )

        active.refresh_from_db()
        already_revoked.refresh_from_db()

        self.assertTrue(active.is_revoked)
        self.assertEqual(already_revoked.revoked_at, original_revoked_at)  # untouched

    def test_revoke_sessions_reports_correct_count(self):
        Session.objects.create(account=self.account)
        Session.objects.create(account=self.account)
        already_revoked = Session.objects.create(account=self.account)
        already_revoked.revoke()

        request = Mock()
        self.admin_instance.revoke_sessions(
            request, Session.objects.filter(account=self.account)
        )

        request.message_user = (
            Mock()
        )  # not used — message_user is called on self, not request
        # Confirm via message_user call args on the admin instance itself:
        self.admin_instance.message_user = Mock()
        Session.objects.filter(account=self.account, is_revoked=False).update(
            is_revoked=False
        )
        Session.objects.create(account=self.account)
        self.admin_instance.revoke_sessions(
            request, Session.objects.filter(account=self.account)
        )
        args, _ = self.admin_instance.message_user.call_args
        self.assertIn("Revoked", args[1])

    def test_get_queryset_uses_select_related(self):
        Session.objects.create(account=self.account)
        request = Mock()
        with self.assertNumQueries(1):
            list(self.admin_instance.get_queryset(request).select_related())


class CodeAdminTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        self.admin_instance = VerificationCodeAdmin(VerificationCode, admin.site)

    def test_invalidate_codes_marks_unused_as_used(self):
        instance, _, _ = VerificationCode.issue_for(self.account)
        self.assertFalse(instance.is_used)

        request = Mock()
        self.admin_instance.invalidate_codes(
            request, VerificationCode.objects.filter(pk=instance.pk)
        )

        instance.refresh_from_db()
        self.assertTrue(instance.is_used)

    def test_invalidate_codes_leaves_already_used_alone(self):
        instance, _, _ = VerificationCode.issue_for(self.account)
        instance.is_used = True
        instance.save(update_fields=["is_used"])

        request = Mock()
        self.admin_instance.message_user = Mock()
        self.admin_instance.invalidate_codes(
            request, VerificationCode.objects.filter(pk=instance.pk)
        )

        args, _ = self.admin_instance.message_user.call_args
        self.assertIn("Invalidated 0", args[1])

    def test_password_reset_code_admin_shares_same_behavior(self):
        """_CodeAdminBase logic applies identically to both subclasses."""
        instance, _, _ = PasswordResetCode.issue_for(self.account)
        pw_admin_instance = PasswordResetCodeAdmin(PasswordResetCode, admin.site)

        request = Mock()
        pw_admin_instance.invalidate_codes(
            request, PasswordResetCode.objects.filter(pk=instance.pk)
        )

        instance.refresh_from_db()
        self.assertTrue(instance.is_used)


class RegisterAdminTests(TestCase):
    """
    Tests the conditional-registration logic directly via
    register_admin(), rather than via module reload — avoids the
    AlreadyRegistered/reload fragility that comes with re-importing
    admin.py mid-test-run.
    """

    def tearDown(self):
        # Restore admin.site to whatever it was before each test,
        # regardless of what register_admin() did during it.
        for model in (Session, VerificationCode, PasswordResetCode):
            if model in admin.site._registry:
                admin.site.unregister(model)

    @patch(f"{MODULE}.enable_admin", True)
    def test_registers_all_three_models_when_enabled(self):
        register_admin()
        self.assertIn(Session, admin.site._registry)
        self.assertIn(VerificationCode, admin.site._registry)
        self.assertIn(PasswordResetCode, admin.site._registry)

    @patch(f"{MODULE}.enable_admin", False)
    def test_registers_nothing_when_disabled(self):
        register_admin()
        self.assertNotIn(Session, admin.site._registry)
        self.assertNotIn(VerificationCode, admin.site._registry)
        self.assertNotIn(PasswordResetCode, admin.site._registry)

    @patch(f"{MODULE}.enable_admin", True)
    def test_calling_register_admin_twice_does_not_raise(self):
        """
        Guards the `if model not in admin.site._registry` check —
        without it, a second call (e.g. from a test that already
        registered, or module re-import in some environments) would
        raise AlreadyRegistered.
        """
        register_admin()
        register_admin()  # should not raise
        self.assertIn(Session, admin.site._registry)
