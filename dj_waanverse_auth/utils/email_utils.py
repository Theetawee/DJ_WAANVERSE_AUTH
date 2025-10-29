import secrets
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from dj_waanverse_auth import settings as app_settings
from dj_waanverse_auth.models import AccessCode
from django.utils import timezone
from datetime import timedelta
from django.db import transaction


def send_auth_code_via_email(account):
    if not account.email_address:
        raise ValueError("Account must have an email address to send auth code.")

    now = timezone.now()
    one_minute_ago = now - timedelta(minutes=1)

    existing_code = (
        AccessCode.objects.filter(email_address=account.email_address)
        .order_by("-created_at")
        .first()
    )

    if existing_code and existing_code.created_at > one_minute_ago:
        seconds_remaining = int(
            (existing_code.created_at + timedelta(minutes=1) - now).total_seconds()
        )
        raise ValueError(
            f"A code was recently sent. Please wait {seconds_remaining} seconds before requesting a new one."
        )

    code = f"{secrets.randbelow(900000) + 100000}"

    with transaction.atomic():
        AccessCode.objects.filter(email_address=account.email_address).delete()
        AccessCode.objects.create(
            email_address=account.email_address,
            code=code,
            expires_at=now + timedelta(minutes=5),
        )
    user_name = account.get_full_name()
    context = {"code": code, "user": account, "user_name": user_name}
    html_body = render_to_string("emails/access_code.html", context)
    text_body = strip_tags(html_body)
    subject = f"{app_settings.platform_name} Access Code"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    to_email = [account.email_address]

    email = EmailMultiAlternatives(subject, text_body, from_email, to_email)
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)
