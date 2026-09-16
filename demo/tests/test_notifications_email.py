# tests/test_notifications_email.py
from __future__ import annotations

from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from dj_waanverse_auth.notifications import email as email_notifications

Account = get_user_model()
MODULE = "dj_waanverse_auth.notifications.email"


class ImmediateThread:
    """
    Stand-in for threading.Thread that runs the target synchronously
    on .start() instead of spawning a real OS thread, so content
    assertions (mail.outbox, exceptions) run deterministically
    instead of racing a background thread.
    """

    def __init__(self, target, daemon=None):
        self._target = target

    def start(self):
        self._target()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class VerificationEmailContentTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
        )

    @patch(f"{MODULE}.threading.Thread", new=ImmediateThread)
    def test_code_email_is_sent_with_code_in_html_body(self):
        email_notifications.send_verification_code_email(self.account, "123456")

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ["wave@example.com"])
        self.assertIn("123456", sent.alternatives[0][0])
        self.assertEqual(sent.alternatives[0][1], "text/html")

    @patch(f"{MODULE}.threading.Thread", new=ImmediateThread)
    def test_code_email_has_plaintext_fallback_with_no_html_tags(self):
        email_notifications.send_verification_code_email(self.account, "654321")

        sent = mail.outbox[0]
        self.assertTrue(sent.body)
        self.assertNotIn("<", sent.body)

    @patch(f"{MODULE}.threading.Thread", new=ImmediateThread)
    def test_link_email_includes_token_in_url(self):
        email_notifications.send_verification_link_email(self.account, "abc123token")

        sent = mail.outbox[0]
        self.assertIn("abc123token", sent.alternatives[0][0])

    @patch(f"{MODULE}.threading.Thread", new=ImmediateThread)
    @patch(f"{MODULE}.EmailMultiAlternatives.send", side_effect=Exception("smtp down"))
    def test_send_failure_inside_thread_is_caught_not_raised(self, mock_send):
        # Should not propagate, even though .send() blows up internally.
        email_notifications.send_verification_code_email(self.account, "123456")
        mock_send.assert_called_once()


class VerificationEmailThreadingContractTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
        )

    @patch(f"{MODULE}.threading.Thread")
    def test_sending_dispatches_via_background_thread(self, mock_thread_cls):
        mock_instance = MagicMock()
        mock_thread_cls.return_value = mock_instance

        email_notifications.send_verification_code_email(self.account, "123456")

        mock_thread_cls.assert_called_once()
        _, kwargs = mock_thread_cls.call_args
        self.assertTrue(callable(kwargs.get("target")))
        self.assertTrue(kwargs.get("daemon"))
        mock_instance.start.assert_called_once()
