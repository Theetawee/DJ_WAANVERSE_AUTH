from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from dj_waanverse_auth.models import ResetPasswordToken
from dj_waanverse_auth.serializers.password_serializers import (
    InitiatePasswordResetSerializer,
)
from dj_waanverse_auth.throttles import EmailVerificationThrottle

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([EmailVerificationThrottle])
def initiate_password_reset_view(request):
    """ """
    serializer = InitiatePasswordResetSerializer(data=request.data)
    try:
        if serializer.is_valid():
            serializer.save()
            email = serializer.validated_data["email_address"]
            return Response(
                {
                    "message": "Password reset email sent.",
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
def reset_password_view(request):
    """
    Handles resetting the user's password by validating the provided code and email address.
    """
    email = request.data.get("email")
    code = request.data.get("code")
    new_password = request.data.get("new_password")
    confirm_password = request.data.get("confirm_password")

    # Validate required fields
    if not all([email, code, new_password, confirm_password]):
        return Response(
            {
                "error": "All fields (email, code, new_password, confirm_password) are required."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if new_password != confirm_password:
        return Response(
            {"error": "New password and confirm password do not match."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        validate_password(new_password)
    except Exception as e:
        return Response(
            {"error": "Password validation failed.", "details": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        user = User.objects.get(email_address=email)
    except User.DoesNotExist:
        return Response(
            {"error": "No user found with this email."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        token = ResetPasswordToken.objects.get(account=user, code=code)
        if token.is_expired():
            return Response(
                {"error": "expired_code"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except ResetPasswordToken.DoesNotExist:
        return Response(
            {"error": "invalid_code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.password_last_updated = timezone.now()
    user.save()

    token.delete()

    return Response(
        {"message": "Password reset successful."},
        status=status.HTTP_200_OK,
    )
