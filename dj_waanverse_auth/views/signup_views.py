import logging

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from dj_waanverse_auth.utils.login_utils import handle_login
from dj_waanverse_auth import settings
from dj_waanverse_auth.serializers.signup_serializers import (
    ActivateEmailSerializer,
    ActivatePhoneSerializer,
    EmailVerificationSerializer,
    PhoneNumberVerificationSerializer,
    SignupSerializer,
)

logger = logging.getLogger(__name__)

Account = get_user_model()


class SignupView(APIView):
    """
    Class-based view to handle user signup.

    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        if settings.disable_signup:
            return Response(
                {"error": "Something went wrong"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SignupSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "success"},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


signup_view = SignupView.as_view()


@api_view(["POST"])
@permission_classes([AllowAny])
def send_email_verification_code(request):
    """
    Function-based view to initiate email verification.
    """
    try:
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Email verification code sent successfully.",
                    "expires_in": "10 minutes",
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
@permission_classes([AllowAny])
def activate_email_address(request):
    """
    Function-based view to activate an email address for a user.
    """
    try:
        handle = request.data.get("handle")
        user = request.user
        if handle != "signup" and not user.is_authenticated:
            return Response(
                {"error": "Unable to authenticate. Please login again"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ActivateEmailSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            request.user = user
            if handle == "signup":
                response = handle_login(request, user)
                return response
            else:
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
@permission_classes([AllowAny])
def send_phone_number_verification_code_view(request):
    """
    Function-based view to initiate phone number verification.
    """
    try:

        serializer = PhoneNumberVerificationSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Verification code sent successfully.",
                    "expires_in": "10 minutes",
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([AllowAny])
def activate_phone_number(request):
    """
    Function-based view to activate an phone_number for a user.
    """
    try:
        handle = request.data.get("handle")
        user = request.user

        if handle != "signup" and not user.is_authenticated:
            return Response(
                {"error": "Unable to authenticate. Please login again"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ActivatePhoneSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            if handle == "signup":
                response = handle_login(request, user)
                return response
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
