from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from dj_waanverse_auth.notifications import dispatch
from dj_waanverse_auth.notifications.sms import console_sms_sender

MODULE = "dj_waanverse_auth.notifications.dispatch"


def fake_sms_sender(phone_number: str, message: str) -> None:
    fake_sms_sender.calls.append((phone_number, message))


fake_sms_sender.calls = []


class ConsoleSmsSenderTests(TestCase):
    def test_logs_phone_and_message(self):
        with self.assertLogs(
            "dj_waanverse_auth.notifications.sms", level="INFO"
        ) as captured:
            console_sms_sender("+256700123456", "Your code is 123456")

        self.assertTrue(
            any(
                "+256700123456" in line and "123456" in line for line in captured.output
            )
        )


class GetSmsSenderTests(TestCase):
    @patch(f"{MODULE}.auth_config.sms_sender", None)
    def test_falls_back_to_console_when_unset(self):
        self.assertIs(dispatch.get_sms_sender(), console_sms_sender)

    @patch(f"{MODULE}.auth_config.sms_sender", "")
    def test_falls_back_to_console_when_blank(self):
        self.assertIs(dispatch.get_sms_sender(), console_sms_sender)

    @patch(
        f"{MODULE}.auth_config.sms_sender",
        "tests.test_notifications_sms.fake_sms_sender",
    )
    def test_resolves_configured_dotted_path(self):
        self.assertIs(dispatch.get_sms_sender(), fake_sms_sender)

    @patch(f"{MODULE}.auth_config.sms_sender", "tests.does_not.exist")
    def test_invalid_path_raises_immediately(self):
        # Deliberately NOT caught here — resolution failures are the
        # view's job to swallow (_deliver's broad except), not
        # dispatch's. This confirms that contract explicitly.
        with self.assertRaises(ImportError):
            dispatch.get_sms_sender()


class SendVerificationSmsTests(TestCase):
    def setUp(self):
        fake_sms_sender.calls = []

    @patch(
        f"{MODULE}.auth_config.sms_sender",
        "tests.test_notifications_sms.fake_sms_sender",
    )
    def test_calls_configured_sender_with_formatted_message(self):
        dispatch.send_verification_sms("+256700123456", "123456")

        self.assertEqual(len(fake_sms_sender.calls), 1)
        phone, message = fake_sms_sender.calls[0]
        self.assertEqual(phone, "+256700123456")
        self.assertIn("123456", message)

    def test_uses_console_sender_when_unconfigured(self):
        with self.assertLogs(
            "dj_waanverse_auth.notifications.sms", level="INFO"
        ) as captured:
            dispatch.send_verification_sms("+256700123456", "999999")

        self.assertTrue(any("999999" in line for line in captured.output))
