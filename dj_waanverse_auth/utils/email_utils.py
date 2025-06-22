from django.db import transaction

from dj_waanverse_auth import settings
from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth.services.email_service import EmailService
from dj_waanverse_auth.utils.generators import generate_code
from dj_waanverse_auth.utils.security_utils import (
    get_device,
    get_ip_address,
    get_location_from_ip,
)


def send_login_email(request, user):
    if user.email_address:
        email_manager = EmailService(request=request)
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


def verify_email_address(user):
    if user.email_address and not user.email_verified:
        code = generate_code()
        email_manager = EmailService()
        template_name = "emails/verify_email.html"
        with transaction.atomic():
            if VerificationCode.objects.filter(
                email_address=user.email_address
            ).exists():
                VerificationCode.objects.filter(
                    email_address=user.email_address
                ).delete()

            VerificationCode.objects.create(email_address=user.email_address, code=code)

            # Send email
            email_manager.send_email(
                subject=settings.verification_email_subject,
                template_name=template_name,
                recipient=user.email_address,
                context={"code": code, "user": user},
            )

        return True

    return False
