from django.db import transaction
from django.utils import timezone
from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth.services.email_service import EmailService
from dj_waanverse_auth.utils.generators import generate_verification_code
from dj_waanverse_auth.utils.security_utils import (
    get_device,
    get_ip_address,
    get_location_from_ip,
)
from datetime import timedelta


def send_login_email(request, user):
    if user.email_address and user.email_verified:
        email_manager = EmailService()
        template_name = "emails/login_alert.html"
        ip_address = get_ip_address(request)
        context = {
            "ip_address": ip_address,
            "location": get_location_from_ip(ip_address),
            "device": get_device(request),
            "user": user,
        }
        email_manager.send_email(
            subject=auth_config.login_alert_email_subject,
            template_name=template_name,
            recipient=user.email_address,
            context=context,
        )


def send_login_code_email(user, code):
    if user.email_address and user.email_verified:
        email_manager = EmailService()
        template_name = "emails/login_code.html"
        context = {
            "code": code,
            "user": user,
        }
        email_manager.send_email(
            subject=auth_config.login_code_email_subject,
            template_name=template_name,
            recipient=user.email_address,
            context=context,
        )


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

        # Prevent sending codes too frequently
        if last_code and (now < last_code.expires_at - timedelta(minutes=9)):
            # Assuming original rule: can't resend within 1 minute
            raise Exception(
                "Too many attempts. Please wait for sometime before trying again."
            )

        code = generate_verification_code()
        email_manager = EmailService()
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

            # Send verification email
            email_manager.send_email(
                subject=auth_config.verification_email_subject,
                template_name=template_name,
                recipient=user.email_address,
                context={"code": code, "user": user},
            )

        return True

    return False
