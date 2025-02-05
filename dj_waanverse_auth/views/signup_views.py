import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dj_waanverse_auth import settings
from dj_waanverse_auth.serializers.signup_serializers import (
    ActivateEmailSerializer,
    EmailVerificationSerializer,
)
from dj_waanverse_auth.services.utils import get_serializer_class
from dj_waanverse_auth.throttles import EmailVerificationThrottle

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
            serializer.save()

            return Response(
                data={"msg": "Account created successfully."},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


signup_view = SignupView.as_view()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EmailVerificationThrottle])
def send_email_verification_link(request):
    """
    Function-based view to initiate email verification with a
    """
    try:
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Email verification link sent successfully.",
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
