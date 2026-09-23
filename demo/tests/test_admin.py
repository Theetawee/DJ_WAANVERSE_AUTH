# tests/test_admin.py
from __future__ import annotations

import hashlib
import importlib
from unittest.mock import patch

from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

import dj_waanverse_auth.admin as admin_module
from dj_waanverse_auth.models import PasswordResetCode, Session, VerificationCode

Account = get_user_model()

ADMIN_MODULES = (Session, VerificationCode, PasswordResetCode)

# Confirmed correct against the actual config module.
ENABLE_ADMIN_PATCH_TARGET = "dj_waanverse_auth.config.settings.auth_config.enable_admin"


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _unregister_if_present(*models):
    for model in models:
        if model in site._registry:
            site.unregister(model)


def _reload_admin_with(enable_admin: bool):
    """
    Forces auth_config.enable_admin to the given value and reloads
    dj_waanverse_auth.admin so its module-level `if` re-evaluates.
    Callers are responsible for unregistering before AND after, since
    skipping the `if` branch on a "disabled" reload does NOT undo a
    prior registration left in admin.site._registry.
    """
    with patch(ENABLE_ADMIN_PATCH_TARGET, enable_admin):
        importlib.reload(admin_module)


# ---------------------------------------------------------------------
# The conditional-import behavior itself
# ---------------------------------------------------------------------


class AdminRegistrationToggleTests(TestCase):
    """
    Exercises admin.py's own conditional import — the actual behavior
    under test, since neither branch is guaranteed by default settings.
    """

    def setUp(self):
        _unregister_if_present(*ADMIN_MODULES)

    def tearDown(self):
        _unregister_if_present(*ADMIN_MODULES)
        # Restore admin.py to whatever the real (non-patched) config
        # says, so later tests relying on default import state see it
        # correctly rather than inheriting this test's forced value.
        importlib.reload(admin_module)
        _unregister_if_present(*ADMIN_MODULES)

    def test_models_registered_when_enabled(self):
        _reload_admin_with(True)

        for model in ADMIN_MODULES:
            self.assertIn(model, site._registry)

    def test_models_not_registered_when_disabled(self):
        _reload_admin_with(False)

        for model in ADMIN_MODULES:
            self.assertNotIn(model, site._registry)

    def test_session_admin_class_not_created_when_disabled(self):
        _reload_admin_with(False)

        self.assertFalse(hasattr(admin_module, "SessionAdmin"))

    def test_session_admin_class_created_when_enabled(self):
        _reload_admin_with(True)

        self.assertTrue(hasattr(admin_module, "SessionAdmin"))


# ---------------------------------------------------------------------
# Shared base for everything below that needs admin actually enabled
# ---------------------------------------------------------------------


class AdminEnabledTestCase(TestCase):
    """
    Base for tests that need the admin classes registered, regardless
    of the real project's enable_admin setting. Cleans up registration
    on both ends so classes never collide via AlreadyRegistered.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _unregister_if_present(*ADMIN_MODULES)  # guard against leftover state
        cls._admin_patcher = patch(ENABLE_ADMIN_PATCH_TARGET, True)
        cls._admin_patcher.start()
        importlib.reload(admin_module)

    @classmethod
    def tearDownClass(cls):
        _unregister_if_present(*ADMIN_MODULES)
        cls._admin_patcher.stop()
        importlib.reload(admin_module)
        super().tearDownClass()


# ---------------------------------------------------------------------
# Access / permissions
# ---------------------------------------------------------------------


class AdminAccessTests(AdminEnabledTestCase):
    def setUp(self):
        self.superuser = Account.objects.create_superuser(
            email_address="admin@example.com",
            password="StrongPassword123!",
        )
        self.client.force_login(self.superuser)

    def test_session_add_view_is_blocked(self):
        response = self.client.get(reverse("admin:dj_waanverse_auth_session_add"))
        self.assertEqual(response.status_code, 403)

    def test_verification_code_add_view_is_blocked(self):
        response = self.client.get(
            reverse("admin:dj_waanverse_auth_verificationcode_add")
        )
        self.assertEqual(response.status_code, 403)

    def test_password_reset_code_add_view_is_blocked(self):
        response = self.client.get(
            reverse("admin:dj_waanverse_auth_passwordresetcode_add")
        )
        self.assertEqual(response.status_code, 403)

    def test_session_changelist_loads(self):
        response = self.client.get(
            reverse("admin:dj_waanverse_auth_session_changelist")
        )
        self.assertEqual(response.status_code, 200)

    def test_verification_code_changelist_loads(self):
        response = self.client.get(
            reverse("admin:dj_waanverse_auth_verificationcode_changelist")
        )
        self.assertEqual(response.status_code, 200)

    def test_password_reset_code_changelist_loads(self):
        response = self.client.get(
            reverse("admin:dj_waanverse_auth_passwordresetcode_changelist")
        )
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------
# Session admin: display + revoke action
# ---------------------------------------------------------------------


class SessionAdminActionTests(AdminEnabledTestCase):
    def setUp(self):
        self.superuser = Account.objects.create_superuser(
            email_address="admin@example.com",
            password="StrongPassword123!",
        )
        self.client.force_login(self.superuser)

        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        self.active_session = Session.objects.create(
            account=self.account,
            refresh_token_hash=_hash("token-a"),
            user_agent="Mozilla/5.0 Test Agent",
        )
        self.already_revoked = Session.objects.create(
            account=self.account,
            refresh_token_hash=_hash("token-b"),
            is_revoked=True,
            revoked_at=timezone.now(),
        )

    def test_revoke_sessions_action_revokes_active_session(self):
        self.client.post(
            reverse("admin:dj_waanverse_auth_session_changelist"),
            {
                "action": "revoke_sessions",
                "_selected_action": [str(self.active_session.pk)],
            },
            follow=True,
        )
        self.active_session.refresh_from_db()
        self.assertTrue(self.active_session.is_revoked)
        self.assertIsNotNone(self.active_session.revoked_at)

    def test_revoke_sessions_action_leaves_already_revoked_untouched(self):
        original_revoked_at = self.already_revoked.revoked_at

        self.client.post(
            reverse("admin:dj_waanverse_auth_session_changelist"),
            {
                "action": "revoke_sessions",
                "_selected_action": [str(self.already_revoked.pk)],
            },
            follow=True,
        )
        self.already_revoked.refresh_from_db()
        self.assertEqual(self.already_revoked.revoked_at, original_revoked_at)

    def test_revoke_sessions_action_handles_mixed_selection(self):
        self.client.post(
            reverse("admin:dj_waanverse_auth_session_changelist"),
            {
                "action": "revoke_sessions",
                "_selected_action": [
                    str(self.active_session.pk),
                    str(self.already_revoked.pk),
                ],
            },
            follow=True,
        )
        self.active_session.refresh_from_db()
        self.assertTrue(self.active_session.is_revoked)

    def test_user_agent_short_truncates_long_agent(self):
        long_agent = "A" * 100
        session = Session.objects.create(
            account=self.account,
            refresh_token_hash=_hash("token-c"),
            user_agent=long_agent,
        )
        admin_instance = admin_module.SessionAdmin(Session, site)

        result = admin_instance.user_agent_short(session)

        self.assertTrue(result.endswith("…"))
        self.assertEqual(len(result), 61)  # 60 chars + ellipsis

    def test_user_agent_short_leaves_short_agent_unchanged(self):
        admin_instance = admin_module.SessionAdmin(Session, site)

        result = admin_instance.user_agent_short(self.active_session)

        self.assertEqual(result, "Mozilla/5.0 Test Agent")


# ---------------------------------------------------------------------
# VerificationCode admin: invalidate action
# ---------------------------------------------------------------------


class VerificationCodeAdminActionTests(AdminEnabledTestCase):
    def setUp(self):
        self.superuser = Account.objects.create_superuser(
            email_address="admin@example.com",
            password="StrongPassword123!",
        )
        self.client.force_login(self.superuser)

        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        self.unused_code, _, _ = VerificationCode.issue_for(self.account)

    def test_invalidate_codes_action_marks_code_used(self):
        self.client.post(
            reverse("admin:dj_waanverse_auth_verificationcode_changelist"),
            {
                "action": "invalidate_codes",
                "_selected_action": [str(self.unused_code.pk)],
            },
            follow=True,
        )
        self.unused_code.refresh_from_db()
        self.assertTrue(self.unused_code.is_used)

    def test_invalidate_codes_action_leaves_already_used_untouched(self):
        used_code, _, _ = VerificationCode.issue_for(self.account)
        used_code.is_used = True
        used_code.save(update_fields=["is_used"])

        self.client.post(
            reverse("admin:dj_waanverse_auth_verificationcode_changelist"),
            {
                "action": "invalidate_codes",
                "_selected_action": [str(used_code.pk)],
            },
            follow=True,
        )
        used_code.refresh_from_db()
        self.assertTrue(used_code.is_used)


# ---------------------------------------------------------------------
# PasswordResetCode admin: invalidate action
# ---------------------------------------------------------------------


class PasswordResetCodeAdminActionTests(AdminEnabledTestCase):
    def setUp(self):
        self.superuser = Account.objects.create_superuser(
            email_address="admin@example.com",
            password="StrongPassword123!",
        )
        self.client.force_login(self.superuser)

        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        self.unused_code, _, _ = PasswordResetCode.issue_for(self.account)

    def test_invalidate_codes_action_marks_code_used(self):
        self.client.post(
            reverse("admin:dj_waanverse_auth_passwordresetcode_changelist"),
            {
                "action": "invalidate_codes",
                "_selected_action": [str(self.unused_code.pk)],
            },
            follow=True,
        )
        self.unused_code.refresh_from_db()
        self.assertTrue(self.unused_code.is_used)
