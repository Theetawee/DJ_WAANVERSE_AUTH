# tests/test_checks.py
from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from dj_waanverse_auth.checks import (
    check_authentication_identifiers,
    check_turnstile_config,
)

MODULE = "dj_waanverse_auth.checks.settings"


class CheckTurnstileConfigTests(TestCase):
    @patch(f"{MODULE}.turnstile_enabled", False)
    def test_no_error_when_disabled(self):
        self.assertEqual(check_turnstile_config(None), [])

    @patch(f"{MODULE}.turnstile_enabled", True)
    @patch(f"{MODULE}.turnstile_secret_key", "a-real-secret")
    def test_no_error_when_enabled_with_secret(self):
        self.assertEqual(check_turnstile_config(None), [])

    @patch(f"{MODULE}.turnstile_enabled", True)
    @patch(f"{MODULE}.turnstile_secret_key", None)
    def test_error_when_enabled_without_secret(self):
        errors = check_turnstile_config(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "dj_waanverse_auth.E001")

    @patch(f"{MODULE}.turnstile_enabled", True)
    @patch(f"{MODULE}.turnstile_secret_key", "")
    def test_error_when_enabled_with_blank_secret(self):
        errors = check_turnstile_config(None)
        self.assertEqual(len(errors), 1)


class CheckAuthenticationIdentifiersTests(TestCase):
    @patch(f"{MODULE}.authentication_identifiers", ["email", "phone"])
    def test_no_error_for_valid_identifiers(self):
        self.assertEqual(check_authentication_identifiers(None), [])

    @patch(f"{MODULE}.authentication_identifiers", [])
    def test_error_when_empty(self):
        errors = check_authentication_identifiers(None)
        ids = [e.id for e in errors]
        self.assertIn("dj_waanverse_auth.E002", ids)

    @patch(f"{MODULE}.authentication_identifiers", ["email", "carrier_pigeon"])
    def test_error_for_unknown_identifier(self):
        errors = check_authentication_identifiers(None)
        ids = [e.id for e in errors]
        self.assertIn("dj_waanverse_auth.E003", ids)

    @patch(f"{MODULE}.authentication_identifiers", ["carrier_pigeon"])
    def test_unknown_identifier_does_not_also_fire_empty_error(self):
        """Non-empty-but-invalid should trigger E003, not also E002."""
        errors = check_authentication_identifiers(None)
        ids = [e.id for e in errors]
        self.assertIn("dj_waanverse_auth.E003", ids)
        self.assertNotIn("dj_waanverse_auth.E002", ids)
