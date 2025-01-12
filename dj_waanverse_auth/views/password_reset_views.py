import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from dj_waanverse_auth.serializers.password_serializers import (
    InitiatePasswordResetSerializer,
    ResetPasswordSerializer,
)
from dj_waanverse_auth.throttles import EmailVerificationThrottle

User = get_user_model()

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([EmailVerificationThrottle])
def initiate_password_reset_view(request):
    """Initiate password reset process by sending reset code to user's email."""
    serializer = InitiatePasswordResetSerializer(data=request.data)

    try:
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "If an account exists with this email, you will receive password reset instructions.",
                "status": "code_sent",
            },
            status=status.HTTP_200_OK,
        )
    except serializers.ValidationError as e:
        return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Password reset initiation failed: {str(e)}", exc_info=True)
        return Response(
            {"error": "Unable to process request."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password_view(request):
    """Reset user's password using the provided reset code."""
    serializer = ResetPasswordSerializer(data=request.data)

    try:
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Password has been successfully reset."},
            status=status.HTTP_200_OK,
        )
    except serializers.ValidationError as e:
        return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Password reset failed: {str(e)}", exc_info=True)
        return Response(
            {"error": "Unable to process request."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
