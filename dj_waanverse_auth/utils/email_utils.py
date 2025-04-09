from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.services.email_service import EmailService
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
