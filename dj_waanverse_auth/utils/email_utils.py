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
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

Account = get_user_model()


def _generate_and_send_code(email_address, template_name, subject):
    now = timezone.now()
    one_minute_ago = now - timedelta(minutes=1)

    existing_code = (
        AccessCode.objects.filter(email_address=email_address)
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
        AccessCode.objects.filter(email_address=email_address).delete()
        AccessCode.objects.create(
            email_address=email_address,
            code=code,
            expires_at=now + timedelta(minutes=5),
        )

    context = {"code": code, "email": email_address}
    html_body = render_to_string(template_name, context)
    text_body = strip_tags(html_body)

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    to_email = [email_address]

    email = EmailMultiAlternatives(subject, text_body, from_email, to_email)
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)


def request_code_flow(email, is_signup=False):
    try:
        if email in app_settings.testing_email_addresses:
            if app_settings.is_testing:
                return Response(
                    {"detail": "Authentication code sent to email."},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"detail": "Something went wrong."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account = Account.objects.filter(email_address=email).first()

        if is_signup:
            if account:
                return Response(
                    {"detail": "Account already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            _generate_and_send_code(
                email_address=email,
                template_name="emails/signup_code.html",
                subject=app_settings.signup_code_email_subject,
            )

            return Response(
                {"detail": "Signup code sent to email."},
                status=status.HTTP_200_OK,
            )

        # Login flow
        if not account:
            return Response(
                {"detail": "Account not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        _generate_and_send_code(
            email_address=email,
            template_name="emails/login_code.html",
            subject=app_settings.login_code_email_subject,
        )

        return Response(
            {"detail": "Authentication code sent to email."},
            status=status.HTTP_200_OK,
        )

    except ValueError as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except ValidationError:
        return Response(
            {"detail": "Invalid email address"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
