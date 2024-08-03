from django.contrib.auth import user_logged_in, user_login_failed
from django.dispatch import receiver
from .models import UserLoginActivity
from .utils import get_client_ip
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone


@receiver(user_logged_in)
def log_user_logged_in_success(sender, user, request, **kwargs):
    try:
        ip_address = get_client_ip(request)
        subject = "Security alert"
        title = "A new login has been detected"
        user_agent_info = (request.META.get("HTTP_USER_AGENT", "<unknown>")[:255],)
        user_login_activity_log = UserLoginActivity(
            login_IP=ip_address,
            login_username=user.username,
            user_agent_info=user_agent_info,
            status=UserLoginActivity.SUCCESS,
        )
        user_login_activity_log.save()
        context = {
            "ip_address": ip_address,
            "subject": subject,
            "title": title,
            "year": timezone.now().year,
            "username": user.username,
            "email": user.email,
            "time": user_login_activity_log.login_datetime,
            "name": user.name,
        }

        receiver_email = user.email
        template_name = "emails/successful_login.html"
        convert_to_html_content = render_to_string(
            template_name=template_name, context=context
        )
        plain_message = strip_tags(convert_to_html_content)
        if settings.DEBUG is False:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[
                    receiver_email,
                ],
                html_message=convert_to_html_content,
                fail_silently=True,
            )

    except Exception as e:
        print(e)


@receiver(user_login_failed)
def log_user_logged_in_failed(sender, credentials, request, **kwargs):
    try:
        user_agent_info = (request.META.get("HTTP_USER_AGENT", "<unknown>")[:255],)
        user_login_activity_log = UserLoginActivity(
            login_IP=get_client_ip(request),
            login_username=credentials["username"],
            user_agent_info=user_agent_info,
            status=UserLoginActivity.FAILED,
        )
        user_login_activity_log.save()
    except Exception as e:
        # log the error
        print(e)
