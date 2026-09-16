from __future__ import annotations

import logging
import threading
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from dj_waanverse_auth import settings as auth_config

logger = logging.getLogger(__name__)


def _send_threaded(subject: str, html_content: str, to: list[str]) -> None:
    def _send():
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=strip_tags(html_content),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=to,
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
        except Exception:
            logger.exception("Failed to send verification email to %s", to)

    threading.Thread(target=_send, daemon=True).start()


def send_verification_code_email(account, code: str) -> None:
    html_content = render_to_string(
        "emails/account_verification_code.html",
        {"code": code, "account": account},
    )
    _send_threaded(
        auth_config.account_verification_email_subject,
        html_content,
        [account.email_address],
    )


def send_verification_link_email(account, token: str) -> None:
    verify_url = f"{auth_config.frontend_url}/verify?token={token}"
    html_content = render_to_string(
        "emails/account_verification_link.html",
        {"verify_url": verify_url, "account": account},
    )
    _send_threaded(
        auth_config.account_verification_email_subject,
        html_content,
        [account.email_address],
    )
