from django.db import transaction
from django.utils import timezone
from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth.utils.generators import generate_verification_code
from datetime import timedelta

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


def send_login_code_email(user, code):
    if user.email_address and user.email_verified:
        template_name = "emails/login_code.html"
        context = {"code": code, "user": user}

        # Render templates
        html_body = render_to_string(template_name, context)
        text_body = strip_tags(html_body)

        subject = auth_config.login_code_email_subject
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@waanverse.com")
        to_email = [{"email": user.email_address, "name": user.username}]

        email = EmailMultiAlternatives(subject, text_body, from_email, to_email)
        email.attach_alternative(html_body, "text/html")

        # Send
        email.send(fail_silently=False)


def verify_email_address(user):
    """
    Generate and send an email verification code for the given user.
    Stores the expiry time in `expires_at` instead of `created_at`.
    """
    if user.email_address and not user.email_verified:
        now = timezone.now()

        last_code = (
            VerificationCode.objects.filter(email_address=user.email_address)
            .order_by("-expires_at")
            .first()
        )

        # Prevent sending codes too frequently (within 1 minute window)
        if last_code and (now < last_code.expires_at - timedelta(minutes=9)):
            raise Exception(
                "Too many attempts. Please wait for some time before trying again."
            )

        code = generate_verification_code()
        template_name = "emails/verify_email.html"

        with transaction.atomic():
            # Remove old codes
            VerificationCode.objects.filter(email_address=user.email_address).delete()

            # Create new code with expiry 10 minutes from now
            VerificationCode.objects.create(
                email_address=user.email_address,
                code=code,
                expires_at=now + timedelta(minutes=10),
            )

            # Render email content
            context = {"code": code, "user": user}
            html_body = render_to_string(template_name, context)
            text_body = strip_tags(html_body)

            subject = auth_config.verification_email_subject
            from_email = getattr(
                settings, "DEFAULT_FROM_EMAIL", "noreply@waanverse.com"
            )
            to_email = [user.email_address]

            # Send email
            email = EmailMultiAlternatives(subject, text_body, from_email, to_email)
            email.attach_alternative(html_body, "text/html")
            email.send(fail_silently=False)

        return True

    return False
