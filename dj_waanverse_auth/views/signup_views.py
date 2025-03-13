import logging

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dj_waanverse_auth import settings
from dj_waanverse_auth.serializers.signup_serializers import (
    ActivateEmailSerializer,
    ActivatePhoneSerializer,
    EmailVerificationSerializer,
)
from dj_waanverse_auth.services.token_service import TokenService
from dj_waanverse_auth.services.utils import get_serializer_class
from dj_waanverse_auth.throttles import (
    EmailVerificationThrottle,
    PhoneVerificationThrottle,
)

logger = logging.getLogger(__name__)

Account = get_user_model()


class SignupView(APIView):
    """
    Class-based view to handle user signup.

    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        signup_serializer = get_serializer_class(settings.registration_serializer)
        serializer = signup_serializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            user = serializer.save()
            token_manager = TokenService(user=user, request=request)
            basic_serializer = get_serializer_class(
                settings.basic_account_serializer_class
            )

            response = Response(
                status=status.HTTP_201_CREATED,
                data={
                    "user": basic_serializer(user).data,
                },
            )
            res = token_manager.setup_login_cookies(response)
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])
            tokens = res["tokens"]
            response = res["response"]
            response.data["status"] = "success"
            response.data["access_token"] = tokens["access_token"]
            response.data["refresh_token"] = tokens["refresh_token"]
            if user.phone_number:
                response.data["next"] = "verify_phone"
            if user.email_address:
                response.data["next"] = "verify_email"
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


signup_view = SignupView.as_view()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EmailVerificationThrottle])
def add_email_view(request):
    """
    Function-based view to initiate email verification with a
    """
    request_type = request.data.get("type", None)
    resend = request_type == "resend"
    try:
        serializer = EmailVerificationSerializer(
            data=request.data, context={"user": request.user, "is_resend": resend}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Email verification code sent successfully.",
                    "expires_in": f"{settings.verification_email_code_expiry_in_minutes} minutes",
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def activate_email_address(request):
    """
    Function-based view to activate an email address for a user.
    """
    try:
        serializer = ActivateEmailSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Email address activated successfully."},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([PhoneVerificationThrottle])
def add_phone_number_view(request):
    """
    Function-based view to initiate phone number verification.
    """
    request_type = request.data.get("type")
    resend = request_type == "resend"

    try:
        serializer_class = get_serializer_class(
            settings.phone_number_verification_serializer
        )
        serializer = serializer_class(
            data=request.data, context={"is_resend": resend, "user": request.user}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Verification code sent successfully.",
                    "expires_in": f"{settings.verification_email_code_expiry_in_minutes} minutes",
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def activate_phone_number(request):
    """
    Function-based view to activate an phone_number for a user.
    """
    try:
        serializer = ActivatePhoneSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "PhoneNumber activated successfully."},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_account_status(request):
    user = request.user
    account_status = request.data.get("status", None)
    if account_status not in ["completed", "incomplete"]:
        return Response(
            {"error": "Invalid status provided"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if account_status == "completed":
        user.is_account_completed = True
    elif account_status == "incomplete":
        user.is_account_completed = False
    user.save()

    return Response(
        {"message": "Account completed successfully."},
        status=status.HTTP_200_OK,
    )
