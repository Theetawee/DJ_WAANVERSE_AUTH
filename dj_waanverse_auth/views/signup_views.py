import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from dj_waanverse_auth.serializers.signup_serializers import (
    InitiateEmailVerificationSerializer,
    VerifyEmailSerializer,
)
from dj_waanverse_auth.services.token_service import TokenService
from dj_waanverse_auth.services.utils import get_serializer_class
from dj_waanverse_auth.settings import auth_config
from dj_waanverse_auth.throttles import EmailVerificationThrottle

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([EmailVerificationThrottle])
def initiate_email_verification(request):
    """ """
    serializer = InitiateEmailVerificationSerializer(data=request.data)
    try:
        if serializer.is_valid():
            serializer.save()
            email = serializer.validated_data["email_address"]
            return Response(
                {
                    "message": "Email verification initiated.",
                    "email_address": email,
                    "status": "code_sent",
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"error": f"Failed to initiate email verification: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_email(request):
    """
    Function-based view to verify email.
    """
    serializer = VerifyEmailSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        email = serializer.validated_data["email_address"]
        return Response(
            {
                "message": "Email verified successfully.",
                "email": email,
                "status": "verified",
            },
            status=status.HTTP_200_OK,
        )
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def signup_view(request):
    """
    Function-based view to handle user signup.
    """
    signup_serializer = get_serializer_class(auth_config.registration_serializer)
    serializer = signup_serializer(data=request.data)
    if serializer.is_valid():
        try:
            user = serializer.save()
            token_manager = TokenService(user=user, request=request)
            response = Response(
                {
                    "status": "success",
                    "user": get_serializer_class(
                        auth_config.basic_account_serializer_class
                    )(user).data,
                },
                status=status.HTTP_201_CREATED,
            )
            response_data = token_manager.setup_login_cookies(response=response)
            response = response_data["response"]
            tokens = response_data["tokens"]
            device_id = response_data["device_id"]
            response.data["device_id"] = device_id
            response.data["access_token"] = tokens["access_token"]
            response.data["refresh_token"] = tokens["refresh_token"]

            return response
        except Exception as e:
            token_manager = TokenService(request=request)
            return token_manager.clear_all_cookies(
                response=(
                    Response(
                        {"error": f"Failed to create account: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                )
            )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
