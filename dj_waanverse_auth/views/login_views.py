import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from dj_waanverse_auth.serializers.login_serializers import LoginSerializer
from dj_waanverse_auth.services import token_service
from dj_waanverse_auth.services.mfa_service import MFAHandler
from dj_waanverse_auth.utils.login_utils import handle_login

logger = logging.getLogger(__name__)


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

            response = handle_login(request=request, user=user, mfa=mfa)
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
        response = handle_login(request=request, user=user)

        return response
    else:
        return Response(
            {"error": "Invalid MFA code or recovery code."},
            status=status.HTTP_400_BAD_REQUEST,
        )
