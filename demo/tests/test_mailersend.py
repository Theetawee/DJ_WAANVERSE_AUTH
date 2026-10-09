from email.mime.text import MIMEText
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.core.mail import (
    EmailMessage,
    EmailMultiAlternatives,
    get_connection,
    send_mail,
    send_mass_mail,
)
from django.test import SimpleTestCase, override_settings

from dj_waanverse_auth import (
    backends as backend,
)

BACKEND_PATH = f"{backend.__name__}.EmailBackend"
OK = SimpleNamespace(success=True, status_code=202, data={})


class FakeBuilder:
    """Records what the backend asks the SDK builder to do; build() returns it as a dict."""

    def __init__(self):
        self.data = {}

    def from_email(self, email, name=None):
        self.data["from"] = {"email": email, "name": name}
        return self

    def to_many(self, recipients):
        self.data["to"] = recipients
        return self

    def cc(self, recipients):
        self.data["cc"] = recipients
        return self

    def bcc(self, recipients):
        self.data["bcc"] = recipients
        return self

    def reply_to(self, email, name=None):
        self.data["reply_to"] = {"email": email, "name": name}
        return self

    def attach_content(self, content, filename, disposition="attachment"):
        self.data.setdefault("attachments", []).append(
            {"filename": filename, "content": content}
        )
        return self

    def subject(self, subject):
        self.data["subject"] = subject
        return self

    def html(self, html):
        self.data["html"] = html
        return self

    def text(self, text):
        self.data["text"] = text
        return self

    def build(self):
        return self.data


@override_settings(
    MAILERSEND_API_KEY="test-key",
    DEFAULT_FROM_EMAIL="noreply@example.com",
    DEFAULT_FROM_NAME="Jaitod",
)
class BackendTestCase(SimpleTestCase):
    def setUp(self):
        client_patch = patch.object(backend, "MailerSendClient")
        self.client_cls = client_patch.start()
        self.addCleanup(client_patch.stop)

        builder_patch = patch.object(backend, "EmailBuilder", FakeBuilder)
        builder_patch.start()
        self.addCleanup(builder_patch.stop)

        self.client = self.client_cls.return_value
        self.client.emails.send.return_value = OK

    def send(self, *messages, **backend_kwargs):
        return backend.EmailBackend(**backend_kwargs).send_messages(list(messages))

    def simple(self, subject="Hi", to="a@example.com"):
        return EmailMessage(subject, "body", to=[to])

    @property
    def requests(self):
        return [call.args[0] for call in self.client.emails.send.call_args_list]


class BodyTests(BackendTestCase):
    def test_plain_text_email_goes_out_as_text_only(self):
        self.send(EmailMessage("Hi", "Line one\nLine two", to=["a@example.com"]))

        req = self.requests[0]
        self.assertEqual(req["text"], "Line one\nLine two")
        self.assertNotIn("html", req)  # plain text must not be sent as HTML
        self.assertEqual(req["subject"], "Hi")

    def test_html_alternative_is_sent_with_the_plain_body_as_text(self):
        msg = EmailMultiAlternatives("Hi", "plain version", to=["a@example.com"])
        msg.attach_alternative("<p>html version</p>", "text/html")

        self.send(msg)

        req = self.requests[0]
        self.assertEqual(req["html"], "<p>html version</p>")
        self.assertEqual(req["text"], "plain version")

    def test_text_part_is_generated_when_only_html_is_given(self):
        msg = EmailMultiAlternatives("Hi", "", to=["a@example.com"])
        msg.attach_alternative("<p>Hello <b>Tee</b></p>", "text/html")

        self.send(msg)

        self.assertEqual(self.requests[0]["text"], "Hello Tee")

    def test_content_subtype_html_body_is_sent_as_html(self):
        msg = EmailMessage("Hi", "<p>Hello <b>Tee</b></p>", to=["a@example.com"])
        msg.content_subtype = "html"

        self.send(msg)

        req = self.requests[0]
        self.assertEqual(req["html"], "<p>Hello <b>Tee</b></p>")
        self.assertEqual(req["text"], "Hello Tee")

    def test_non_html_alternatives_are_ignored(self):
        msg = EmailMultiAlternatives("Hi", "plain", to=["a@example.com"])
        msg.attach_alternative("{}", "application/json")

        self.send(msg)

        self.assertNotIn("html", self.requests[0])

    def test_email_with_no_body_raises_and_sends_nothing(self):
        with self.assertRaises(ValueError):
            self.send(EmailMessage("Hi", "", to=["a@example.com"]))

        self.client.emails.send.assert_not_called()


class RecipientTests(BackendTestCase):
    def test_every_to_recipient_is_included(self):
        self.send(
            EmailMessage(
                "Hi", "body", to=["a@example.com", "b@example.com", "c@example.com"]
            )
        )

        self.assertEqual(
            self.requests[0]["to"],
            [
                {"email": "a@example.com"},
                {"email": "b@example.com"},
                {"email": "c@example.com"},
            ],
        )

    def test_display_names_are_split_from_the_address(self):
        self.send(EmailMessage("Hi", "body", to=["Tee Kay <tee@example.com>"]))

        self.assertEqual(
            self.requests[0]["to"], [{"email": "tee@example.com", "name": "Tee Kay"}]
        )

    def test_dict_recipients_are_still_accepted(self):
        msg = EmailMessage(
            "Hi", "body", to=[{"email": "tee@example.com", "name": "Tee"}]
        )

        self.send(msg)

        self.assertEqual(
            self.requests[0]["to"], [{"email": "tee@example.com", "name": "Tee"}]
        )

    def test_cc_and_bcc_are_passed_through(self):
        msg = EmailMessage(
            "Hi",
            "body",
            to=["a@example.com"],
            cc=["cc@example.com"],
            bcc=["Audit <audit@example.com>"],
        )

        self.send(msg)

        req = self.requests[0]
        self.assertEqual(req["cc"], [{"email": "cc@example.com"}])
        self.assertEqual(req["bcc"], [{"email": "audit@example.com", "name": "Audit"}])

    def test_cc_and_bcc_are_left_out_when_empty(self):
        self.send(self.simple())

        req = self.requests[0]
        self.assertNotIn("cc", req)
        self.assertNotIn("bcc", req)

    def test_email_with_only_bcc_raises_because_mailersend_needs_a_to(self):
        with self.assertRaises(ValueError):
            self.send(EmailMessage("Hi", "body", bcc=["audit@example.com"]))

        self.client.emails.send.assert_not_called()

    def test_invalid_address_raises(self):
        with self.assertRaises(ValueError):
            self.send(EmailMessage("Hi", "body", to=["not-an-address"]))

        self.client.emails.send.assert_not_called()


class SenderTests(BackendTestCase):
    def test_default_sender_uses_default_from_name(self):
        self.send(self.simple())

        self.assertEqual(
            self.requests[0]["from"], {"email": "noreply@example.com", "name": "Jaitod"}
        )

    def test_default_from_name_falls_back_to_no_reply(self):
        with override_settings():
            del settings.DEFAULT_FROM_NAME
            self.send(self.simple())

        self.assertEqual(self.requests[0]["from"]["name"], "No Reply")

    def test_display_name_inside_default_from_email_is_used(self):
        with override_settings(DEFAULT_FROM_EMAIL="Jaitod Team <hello@example.com>"):
            self.send(self.simple())

        self.assertEqual(
            self.requests[0]["from"],
            {"email": "hello@example.com", "name": "Jaitod Team"},
        )

    def test_message_from_email_is_respected(self):
        msg = EmailMessage(
            "Hi",
            "body",
            from_email="Support <support@example.com>",
            to=["a@example.com"],
        )

        self.send(msg)

        self.assertEqual(
            self.requests[0]["from"],
            {"email": "support@example.com", "name": "Support"},
        )

    def test_default_name_is_not_applied_to_a_different_address(self):
        msg = EmailMessage(
            "Hi", "body", from_email="support@example.com", to=["a@example.com"]
        )

        self.send(msg)

        self.assertEqual(
            self.requests[0]["from"], {"email": "support@example.com", "name": None}
        )

    def test_explicit_name_wins_for_the_default_address(self):
        msg = EmailMessage(
            "Hi",
            "body",
            from_email="Billing <noreply@example.com>",
            to=["a@example.com"],
        )

        self.send(msg)

        self.assertEqual(self.requests[0]["from"]["name"], "Billing")


class ConfigTests(BackendTestCase):
    def test_no_messages_returns_zero_without_touching_the_sdk(self):
        self.assertEqual(backend.EmailBackend().send_messages([]), 0)

        self.client_cls.assert_not_called()

    def test_client_is_created_once_with_the_api_key(self):
        self.send(self.simple(), self.simple(), self.simple())

        self.client_cls.assert_called_once_with(api_key="test-key")

    def test_empty_api_key_raises(self):
        with override_settings(MAILERSEND_API_KEY=""):
            with self.assertRaisesMessage(ValueError, "MAILERSEND_API_KEY"):
                self.send(self.simple())

    def test_missing_api_key_setting_raises_value_error_not_attribute_error(self):
        with override_settings():
            del settings.MAILERSEND_API_KEY
            with self.assertRaisesMessage(ValueError, "MAILERSEND_API_KEY"):
                self.send(self.simple())

    def test_empty_default_from_email_raises(self):
        with override_settings(DEFAULT_FROM_EMAIL=""):
            with self.assertRaisesMessage(ValueError, "DEFAULT_FROM_EMAIL"):
                self.send(
                    EmailMessage(
                        "Hi", "body", from_email="x@example.com", to=["a@example.com"]
                    )
                )

    def test_misconfiguration_raises_even_with_fail_silently(self):
        with override_settings(MAILERSEND_API_KEY=""):
            with self.assertRaises(ValueError):
                self.send(self.simple(), fail_silently=True)


class SendingTests(BackendTestCase):
    def test_returns_the_number_of_messages_sent(self):
        count = self.send(self.simple("one"), self.simple("two"), self.simple("three"))

        self.assertEqual(count, 3)
        self.assertEqual([r["subject"] for r in self.requests], ["one", "two", "three"])

    def test_failure_raises_by_default_and_stops(self):
        self.client.emails.send.side_effect = [OK, RuntimeError("api down"), OK]

        with self.assertRaisesMessage(RuntimeError, "api down"):
            self.send(self.simple("one"), self.simple("two"), self.simple("three"))

        self.assertEqual(
            self.client.emails.send.call_count, 2
        )  # third was never attempted

    def test_fail_silently_swallows_errors_logs_them_and_continues(self):
        self.client.emails.send.side_effect = [RuntimeError("api down"), OK]

        with self.assertLogs(backend.logger.name, level="ERROR") as logs:
            count = self.send(
                self.simple("first"), self.simple("second"), fail_silently=True
            )

        self.assertEqual(count, 1)  # only the one that actually went out
        self.assertEqual(self.client.emails.send.call_count, 2)
        self.assertIn("first", "\n".join(logs.output))

    def test_api_key_never_appears_in_logs(self):
        self.client.emails.send.side_effect = RuntimeError("api down")

        with self.assertLogs(backend.logger.name, level="ERROR") as logs:
            self.send(self.simple(), fail_silently=True)

        self.assertNotIn("test-key", "\n".join(logs.output))

    def test_unsuccessful_response_counts_as_a_failure(self):
        self.client.emails.send.return_value = SimpleNamespace(
            success=False,
            status_code=422,
            data={"message": "The from.email must be verified"},
        )

        with self.assertRaises(backend.MailerSendDeliveryError) as ctx:
            self.send(self.simple())

        self.assertIn("422", str(ctx.exception))
        self.assertIn("must be verified", str(ctx.exception))

    def test_unsuccessful_response_with_fail_silently_returns_zero_and_logs(self):
        self.client.emails.send.return_value = SimpleNamespace(
            success=False, status_code=429, data={}
        )

        with self.assertLogs(backend.logger.name, level="ERROR"):
            count = self.send(self.simple(), fail_silently=True)

        self.assertEqual(count, 0)

    def test_client_creation_failure_raises_by_default(self):
        self.client_cls.side_effect = RuntimeError("bad key format")

        with self.assertRaisesMessage(RuntimeError, "bad key format"):
            self.send(self.simple())

    def test_client_creation_failure_with_fail_silently_returns_zero(self):
        self.client_cls.side_effect = RuntimeError("bad key format")

        with self.assertLogs(backend.logger.name, level="ERROR"):
            count = self.send(self.simple(), fail_silently=True)

        self.assertEqual(count, 0)

    def test_tuple_attachments_are_passed_to_the_sdk(self):
        msg = EmailMessage(
            "Invoice",
            "body",
            to=["a@example.com"],
            attachments=[
                ("invoice.pdf", b"%PDF-bytes", "application/pdf"),
                ("notes.txt", "hello", "text/plain"),
            ],
        )

        self.send(msg)

        self.assertEqual(
            self.requests[0]["attachments"],
            [
                {"filename": "invoice.pdf", "content": b"%PDF-bytes"},
                {"filename": "notes.txt", "content": "hello"},
            ],
        )

    def test_mime_attachments_are_passed_to_the_sdk(self):
        part = MIMEText("from a mime part", "plain")
        part.add_header("Content-Disposition", "attachment", filename="mime.txt")
        msg = EmailMessage("Hi", "body", to=["a@example.com"])
        msg.attach(part)

        self.send(msg)

        self.assertEqual(
            self.requests[0]["attachments"],
            [{"filename": "mime.txt", "content": b"from a mime part"}],
        )

    def test_no_attachments_key_when_there_are_none(self):
        self.send(self.simple())

        self.assertNotIn("attachments", self.requests[0])

    def test_reply_to_is_passed_to_the_sdk(self):
        msg = EmailMessage(
            "Hi",
            "body",
            to=["a@example.com"],
            reply_to=["Support <support@example.com>"],
        )

        self.send(msg)

        self.assertEqual(
            self.requests[0]["reply_to"],
            {"email": "support@example.com", "name": "Support"},
        )

    def test_reply_to_left_out_when_not_set(self):
        self.send(self.simple())

        self.assertNotIn("reply_to", self.requests[0])

    def test_only_the_first_reply_to_is_used_and_the_rest_are_logged(self):
        msg = EmailMessage(
            "Hi",
            "body",
            to=["a@example.com"],
            reply_to=["one@example.com", "two@example.com"],
        )

        with self.assertLogs(backend.logger.name, level="WARNING") as logs:
            count = self.send(msg)

        self.assertEqual(count, 1)
        self.assertEqual(self.requests[0]["reply_to"]["email"], "one@example.com")
        self.assertIn("reply-to", "\n".join(logs.output))


class DjangoIntegrationTests(BackendTestCase):
    """
    Through Django's own mail API only. Anything in your project that sends mail with
    send_mail / EmailMultiAlternatives works with this backend, and switching
    EMAIL_BACKEND to another backend later needs no changes anywhere else.
    """

    def test_send_mail_with_the_configured_backend(self):
        with self.settings(EMAIL_BACKEND=BACKEND_PATH):
            count = send_mail("Hi", "hello", None, ["a@example.com"])

        self.assertEqual(count, 1)
        req = self.requests[0]
        self.assertEqual(req["subject"], "Hi")
        self.assertEqual(req["text"], "hello")
        self.assertEqual(
            req["from"], {"email": "noreply@example.com", "name": "Jaitod"}
        )

    def test_send_mail_with_get_connection(self):
        connection = get_connection(BACKEND_PATH)

        count = send_mail("Hi", "hello", None, ["a@example.com"], connection=connection)

        self.assertEqual(count, 1)

    def test_send_mail_with_html_message(self):
        with self.settings(EMAIL_BACKEND=BACKEND_PATH):
            send_mail(
                "Hi", "plain", None, ["a@example.com"], html_message="<p>rich</p>"
            )

        req = self.requests[0]
        self.assertEqual(req["html"], "<p>rich</p>")
        self.assertEqual(req["text"], "plain")

    def test_email_multi_alternatives_send(self):
        msg = EmailMultiAlternatives(
            "Hi", "plain", to=["a@example.com"], cc=["c@example.com"]
        )
        msg.attach_alternative("<p>rich</p>", "text/html")

        with self.settings(EMAIL_BACKEND=BACKEND_PATH):
            count = msg.send()

        self.assertEqual(count, 1)
        self.assertEqual(self.requests[0]["html"], "<p>rich</p>")
        self.assertEqual(self.requests[0]["cc"], [{"email": "c@example.com"}])

    def test_send_mass_mail_reuses_one_client(self):
        datatuple = (
            ("One", "body 1", None, ["a@example.com"]),
            ("Two", "body 2", None, ["b@example.com"]),
            ("Three", "body 3", None, ["c@example.com"]),
        )

        with self.settings(EMAIL_BACKEND=BACKEND_PATH):
            count = send_mass_mail(datatuple)

        self.assertEqual(count, 3)
        self.assertEqual([r["subject"] for r in self.requests], ["One", "Two", "Three"])
        self.client_cls.assert_called_once_with(api_key="test-key")

    def test_send_mail_fail_silently_is_honoured(self):
        self.client.emails.send.side_effect = RuntimeError("api down")

        with self.settings(EMAIL_BACKEND=BACKEND_PATH):
            with self.assertLogs(backend.logger.name, level="ERROR"):
                count = send_mail(
                    "Hi", "hello", None, ["a@example.com"], fail_silently=True
                )

        self.assertEqual(count, 0)

    def test_send_mail_raises_without_fail_silently(self):
        self.client.emails.send.side_effect = RuntimeError("api down")

        with self.settings(EMAIL_BACKEND=BACKEND_PATH):
            with self.assertRaises(RuntimeError):
                send_mail("Hi", "hello", None, ["a@example.com"])

    def test_send_mail_raises_when_mailersend_rejects_the_email(self):
        self.client.emails.send.return_value = SimpleNamespace(
            success=False, status_code=422, data={}
        )

        with self.settings(EMAIL_BACKEND=BACKEND_PATH):
            with self.assertRaises(backend.MailerSendDeliveryError):
                send_mail("Hi", "hello", None, ["a@example.com"])


@override_settings(
    MAILERSEND_API_KEY="test-key",
    DEFAULT_FROM_EMAIL="noreply@example.com",
    DEFAULT_FROM_NAME="Jaitod",
)
class RealSdkContractTests(SimpleTestCase):
    """
    Uses the real EmailBuilder, no fakes and no network. If the SDK renames a method
    or starts rejecting what the backend builds, these fail.
    """

    def build(self, message):
        return (
            backend.EmailBackend()._build_request(message).model_dump(exclude_none=True)
        )

    def test_html_text_cc_bcc_and_display_names(self):
        msg = EmailMultiAlternatives(
            "Hi",
            "plain",
            "Support <support@example.com>",
            ["Tee <tee@example.com>", "b@example.com"],
            cc=["cc@example.com"],
            bcc=["Audit <audit@example.com>"],
        )
        msg.attach_alternative("<p>html</p>", "text/html")

        data = self.build(msg)

        self.assertEqual(
            data["from_email"], {"email": "support@example.com", "name": "Support"}
        )
        self.assertEqual(
            data["to"],
            [{"email": "tee@example.com", "name": "Tee"}, {"email": "b@example.com"}],
        )
        self.assertEqual(data["cc"], [{"email": "cc@example.com"}])
        self.assertEqual(data["bcc"], [{"email": "audit@example.com", "name": "Audit"}])
        self.assertEqual(data["subject"], "Hi")
        self.assertEqual(data["html"], "<p>html</p>")
        self.assertEqual(data["text"], "plain")

    def test_default_sender_with_name(self):
        data = self.build(EmailMessage("Hi", "body", to=["a@example.com"]))

        self.assertEqual(
            data["from_email"], {"email": "noreply@example.com", "name": "Jaitod"}
        )

    def test_text_only(self):
        data = self.build(EmailMessage("Hi", "plain only", to=["a@example.com"]))

        self.assertEqual(data["text"], "plain only")
        self.assertNotIn("html", data)

    def test_html_only(self):
        msg = EmailMessage("Hi", "<p>html only</p>", to=["a@example.com"])
        msg.content_subtype = "html"

        data = self.build(msg)

        self.assertEqual(data["html"], "<p>html only</p>")
        self.assertEqual(data["text"], "html only")

    def test_reply_to_and_attachments(self):
        msg = EmailMessage(
            "Invoice",
            "body",
            to=["a@example.com"],
            reply_to=["Support <support@example.com>"],
            attachments=[("a.txt", "hello", "text/plain")],
        )

        data = self.build(msg)

        self.assertEqual(
            data["reply_to"], {"email": "support@example.com", "name": "Support"}
        )
        self.assertEqual(
            data["attachments"],
            [
                {
                    "filename": "a.txt",
                    "disposition": "attachment",
                    "content": "aGVsbG8=",
                }
            ],  # base64 of "hello"
        )
