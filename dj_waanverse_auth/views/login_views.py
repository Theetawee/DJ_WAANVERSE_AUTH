import logging

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.security.utils import (
    get_device,
    get_ip_address,
    get_location_from_ip,
)
from dj_waanverse_auth.serializers.login_serializers import LoginSerializer
from dj_waanverse_auth.services import token_service
from dj_waanverse_auth.services.email_service import EmailPriority, EmailService
from dj_waanverse_auth.services.mfa_service import MFAHandler
from dj_waanverse_auth.services.utils import get_serializer_class

logger = logging.getLogger(__name__)


def send_login_email(request, user):
    email_manager = EmailService(request=request)
    template_name = "emails/login_alert.html"
    ip_address = get_ip_address(request)
    context = {
        "ip_address": ip_address,
        "location": get_location_from_ip(ip_address),
        "device": get_device(request),
    }
    email_manager.send_email(
        subject=auth_config.login_alert_email_subject,
        template_name=template_name,
        priority=EmailPriority.HIGH,
        recipient=user.email_address,
        context=context,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """View for user login."""
    try:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            mfa = serializer.validated_data["mfa"]
            token_manager = token_service.TokenService(user=user, request=request)

            if mfa:
                response = Response(
                    data={"status": "success", "mfa": user.id},
                    status=status.HTTP_200_OK,
                )
                response = token_manager.clear_all_cookies(response)
                return response
            else:
                basic_serializer = get_serializer_class(
                    auth_config.basic_account_serializer_class
                )
                response = Response(
                    data={
                        "status": "success",
                        "user": basic_serializer(user).data,
                    },
                    status=status.HTTP_200_OK,
                )
                user.last_login = timezone.now()
                user.save(update_fields=["last_login"])

                response_data = token_manager.setup_login_cookies(response=response)
                response = response_data["response"]
                tokens = response_data["tokens"]
                response.data["access_token"] = tokens["access_token"]
                response.data["refresh_token"] = tokens["refresh_token"]
                if (
                    auth_config.email_security_notifications_enabled
                    and user.can_receive_emails
                ):
                    send_login_email(request, user)
                return response
        else:
            token_manager = token_service.TokenService(request=request)
            response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            response = token_manager.clear_all_cookies(response)
            return response

    except Exception as e:
        logger.exception(f"Error occurred while logging in. Error: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def mfa_login_view(request):
    """Handle MFA login using a provided MFA or recovery code."""
    # Retrieve MFA cookie with user ID
    user_id = request.data.get("user_id", None)
    is_valid = False
    if not user_id:
        return Response(
            {
                "error": "Unable to authenticate. Please login again",
                "code": "mfa_cookie_not_found",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = get_user_model().objects.get(id=int(user_id))
    except get_user_model().DoesNotExist:
        return Response(
            {
                "error": "Unable to authenticate. Please login again",
                "code": "user_not_found",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    mfa_handler = MFAHandler(user)

    code = request.data.get("code")

    if not code:
        return Response(
            {"error": "MFA code or recovery code is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if mfa_handler.verify_token(code):
        is_valid = True
    if is_valid:
        token_manager = token_service.TokenService(user=user, request=request)
        basic_serializer = get_serializer_class(
            auth_config.basic_account_serializer_class
        )

        response = Response(
            data={
                "status": "success",
                "user": basic_serializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        response_data = token_manager.setup_login_cookies(response=response)
        response = response_data["response"]
        tokens = response_data["tokens"]
        response.data["access_token"] = tokens["access_token"]
        response.data["refresh_token"] = tokens["refresh_token"]
        if auth_config.email_security_notifications_enabled and user.can_receive_emails:
            send_login_email(request, user)

        return response
    else:
        return Response(
            {"error": "Invalid MFA code or recovery code."},
            status=status.HTTP_400_BAD_REQUEST,
        )
