# tests/test_turnstile.py
from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from dj_waanverse_auth.utils.security.turnstile import verify_turnstile_token

MODULE = "dj_waanverse_auth.utils.security.turnstile"


def _mock_response(success: bool, status_code: int = 200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = {"success": success}
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError("bad status")
    return response


class VerifyTurnstileTokenTests(TestCase):
    # ------------------------------------------------------------------
    # Disabled — always passes, no network call at all
    # ------------------------------------------------------------------

    @patch(f"{MODULE}.auth_config.turnstile_enabled", False)
    @patch(f"{MODULE}.requests.post")
    def test_returns_true_when_disabled_regardless_of_token(self, mock_post):
        self.assertTrue(verify_turnstile_token(None))
        self.assertTrue(verify_turnstile_token("anything"))
        mock_post.assert_not_called()

    # ------------------------------------------------------------------
    # Enabled — missing token
    # ------------------------------------------------------------------

    @patch(f"{MODULE}.auth_config.turnstile_enabled", True)
    @patch(f"{MODULE}.auth_config.turnstile_secret_key", "secret")
    @patch(f"{MODULE}.requests.post")
    def test_returns_false_for_missing_token_without_calling_api(self, mock_post):
        self.assertFalse(verify_turnstile_token(None))
        self.assertFalse(verify_turnstile_token(""))
        mock_post.assert_not_called()

    # ------------------------------------------------------------------
    # Enabled — missing secret is a config error, not a soft failure
    # ------------------------------------------------------------------

    @patch(f"{MODULE}.auth_config.turnstile_enabled", True)
    @patch(f"{MODULE}.auth_config.turnstile_secret_key", None)
    def test_raises_improperly_configured_when_secret_missing(self):
        with self.assertRaises(ImproperlyConfigured):
            verify_turnstile_token("some-token")

    @patch(f"{MODULE}.auth_config.turnstile_enabled", True)
    @patch(f"{MODULE}.auth_config.turnstile_secret_key", "")
    def test_raises_improperly_configured_when_secret_is_blank_string(self):
        with self.assertRaises(ImproperlyConfigured):
            verify_turnstile_token("some-token")

    # ------------------------------------------------------------------
    # Enabled — real verification outcomes
    # ------------------------------------------------------------------

    @patch(f"{MODULE}.auth_config.turnstile_enabled", True)
    @patch(f"{MODULE}.auth_config.turnstile_secret_key", "secret")
    @patch(f"{MODULE}.requests.post")
    def test_returns_true_when_cloudflare_reports_success(self, mock_post):
        mock_post.return_value = _mock_response(success=True)
        self.assertTrue(verify_turnstile_token("valid-token"))

    @patch(f"{MODULE}.auth_config.turnstile_enabled", True)
    @patch(f"{MODULE}.auth_config.turnstile_secret_key", "secret")
    @patch(f"{MODULE}.requests.post")
    def test_returns_false_when_cloudflare_reports_failure(self, mock_post):
        mock_post.return_value = _mock_response(success=False)
        self.assertFalse(verify_turnstile_token("invalid-token"))

    @patch(f"{MODULE}.auth_config.turnstile_enabled", True)
    @patch(f"{MODULE}.auth_config.turnstile_secret_key", "secret")
    @patch(f"{MODULE}.requests.post")
    def test_sends_secret_and_response_in_payload(self, mock_post):
        mock_post.return_value = _mock_response(success=True)
        verify_turnstile_token("the-token")

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"]["secret"], "secret")
        self.assertEqual(kwargs["data"]["response"], "the-token")

    @patch(f"{MODULE}.auth_config.turnstile_enabled", True)
    @patch(f"{MODULE}.auth_config.turnstile_secret_key", "secret")
    @patch(f"{MODULE}.requests.post")
    def test_includes_remote_ip_when_provided(self, mock_post):
        mock_post.return_value = _mock_response(success=True)
        verify_turnstile_token("the-token", remote_ip="203.0.113.5")

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"]["remoteip"], "203.0.113.5")

    @patch(f"{MODULE}.auth_config.turnstile_enabled", True)
    @patch(f"{MODULE}.auth_config.turnstile_secret_key", "secret")
    @patch(f"{MODULE}.requests.post")
    def test_omits_remote_ip_when_not_provided(self, mock_post):
        mock_post.return_value = _mock_response(success=True)
        verify_turnstile_token("the-token", remote_ip=None)

        _, kwargs = mock_post.call_args
        self.assertNotIn("remoteip", kwargs["data"])

    # ------------------------------------------------------------------
    # Fail closed on network problems — the important security property
    # ------------------------------------------------------------------

    @patch(f"{MODULE}.auth_config.turnstile_enabled", True)
    @patch(f"{MODULE}.auth_config.turnstile_secret_key", "secret")
    @patch(f"{MODULE}.requests.post", side_effect=requests.Timeout("timed out"))
    def test_returns_false_on_timeout_not_raises(self, mock_post):
        self.assertFalse(verify_turnstile_token("the-token"))

    @patch(f"{MODULE}.auth_config.turnstile_enabled", True)
    @patch(f"{MODULE}.auth_config.turnstile_secret_key", "secret")
    @patch(
        f"{MODULE}.requests.post", side_effect=requests.ConnectionError("dns failure")
    )
    def test_returns_false_on_connection_error(self, mock_post):
        self.assertFalse(verify_turnstile_token("the-token"))

    @patch(f"{MODULE}.auth_config.turnstile_enabled", True)
    @patch(f"{MODULE}.auth_config.turnstile_secret_key", "secret")
    @patch(f"{MODULE}.requests.post")
    def test_returns_false_on_non_2xx_response(self, mock_post):
        mock_post.return_value = _mock_response(success=True, status_code=500)
        self.assertFalse(verify_turnstile_token("the-token"))
