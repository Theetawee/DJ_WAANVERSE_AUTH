"""
Django email backend for MailerSend (official `mailersend` v2 SDK).

settings.py:

    EMAIL_BACKEND = "yourpackage.mailersend_backend.EmailBackend"
    MAILERSEND_API_KEY = os.environ.get("MAILERSEND_API_KEY", "")
    DEFAULT_FROM_EMAIL = "hello@yourdomain.com"   # or "Name <hello@yourdomain.com>"
    DEFAULT_FROM_NAME = "Jaitod"                  # optional; used when no display name is given

Attachments (tuples or MIME objects) and reply_to are supported. MailerSend accepts a
single reply-to address, so only the first one is used (a warning is logged if there
are more).
"""

import logging
from email.mime.base import MIMEBase
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.utils.html import strip_tags
from mailersend import EmailBuilder, MailerSendClient

logger = logging.getLogger(__name__)


class MailerSendDeliveryError(Exception):
    """MailerSend answered, but did not accept the email."""


def _parse_address(value):
    """
    'Name <a@b.com>', 'a@b.com' or {'email': ..., 'name': ...}
    -> {'email': 'a@b.com', 'name': 'Name' or ''}
    """
    if isinstance(value, dict):
        email, name = value.get("email", ""), value.get("name", "")
    else:
        name, email = parseaddr(str(value))
    email = (email or "").strip()
    name = (name or "").strip()
    if "@" not in email:
        raise ValueError(f"Invalid email address: {value!r}")
    return {"email": email, "name": name}


def _recipient_dicts(values):
    """Recipients in the shape the SDK expects. The name key is left out when empty."""
    recipients = []
    for value in values or []:
        address = _parse_address(value)
        item = {"email": address["email"]}
        if address["name"]:
            item["name"] = address["name"]
        recipients.append(item)
    return recipients


def _attachment_parts(attachment):
    """Django attachments are (filename, content, mimetype) tuples or MIME objects."""
    if isinstance(attachment, MIMEBase):
        return (
            attachment.get_filename() or "attachment",
            attachment.get_payload(decode=True) or b"",
        )
    filename, content, _mimetype = attachment
    return filename or "attachment", content


class EmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, "MAILERSEND_API_KEY", "")
        default_from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "")

        # Misconfiguration is a developer error, so it is raised even with fail_silently.
        if not api_key:
            raise ValueError("MAILERSEND_API_KEY is not set")
        if not default_from_email:
            raise ValueError("DEFAULT_FROM_EMAIL is not set")

        try:
            client = MailerSendClient(api_key=api_key)
        except Exception:
            if not self.fail_silently:
                raise
            logger.exception("Could not create the MailerSend client")
            return 0

        sent = 0
        for message in email_messages:
            try:
                self._send_one(client, message)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
                logger.exception("MailerSend failed to send %r", message.subject)
        return sent

    def _send_one(self, client, message):
        request = self._build_request(message)
        response = client.emails.send(request)

        # Depending on the failure, the SDK either raises or hands back a response
        # object with success=False. Treat the second case as a failure too.
        if getattr(response, "success", True) is False:
            raise MailerSendDeliveryError(
                f"MailerSend rejected {message.subject!r} "
                f"(status {getattr(response, 'status_code', 'unknown')}): "
                f"{getattr(response, 'data', '')}"
            )

    def _build_request(self, message):
        # Sender: message.from_email, falling back to the default. DEFAULT_FROM_NAME
        # is only used for the default address when no display name was given.
        default = _parse_address(settings.DEFAULT_FROM_EMAIL)
        sender = _parse_address(message.from_email or settings.DEFAULT_FROM_EMAIL)
        if not sender["name"] and sender["email"] == default["email"]:
            sender["name"] = default["name"] or getattr(
                settings, "DEFAULT_FROM_NAME", "No Reply"
            )

        to = _recipient_dicts(message.to)
        if not to:
            raise ValueError(f"Email {message.subject!r} has no 'to' recipients")

        # Body: plain emails go out as text only. HTML comes from an html alternative
        # or from content_subtype="html". A missing text part is made from the HTML.
        html = None
        text = None
        if message.content_subtype == "html":
            html = message.body or None
        else:
            text = message.body or None
        for content, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                html = content
                break
        if not html and not text:
            raise ValueError(f"Email {message.subject!r} has no body")
        if html and not text:
            text = strip_tags(html)

        reply_to = _recipient_dicts(message.reply_to)
        if len(reply_to) > 1:
            logger.warning(
                "MailerSend accepts one reply-to address; using the first and ignoring %d other(s) for %r",
                len(reply_to) - 1,
                message.subject,
            )

        builder = EmailBuilder()
        if sender["name"]:
            builder = builder.from_email(sender["email"], sender["name"])
        else:
            builder = builder.from_email(sender["email"])
        builder = builder.to_many(to).subject(message.subject)

        cc = _recipient_dicts(message.cc)
        bcc = _recipient_dicts(message.bcc)
        if cc:
            builder = builder.cc(cc)
        if bcc:
            builder = builder.bcc(bcc)
        if reply_to:
            first = reply_to[0]
            if "name" in first:
                builder = builder.reply_to(first["email"], first["name"])
            else:
                builder = builder.reply_to(first["email"])
        if html:
            builder = builder.html(html)
        if text:
            builder = builder.text(text)
        for attachment in message.attachments:
            filename, content = _attachment_parts(attachment)
            builder = builder.attach_content(content, filename)
        return builder.build()
