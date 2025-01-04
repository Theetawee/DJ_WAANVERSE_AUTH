import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from dj_waanverse_auth.serializers.login_serializers import LoginSerializer
from dj_waanverse_auth.services import email_service, token_service
from dj_waanverse_auth.services.mfa_service import MFAHandler
from dj_waanverse_auth.services.utils import get_serializer_class
from dj_waanverse_auth.settings import auth_config

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """View for user login."""
    try:
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            mfa = serializer.validated_data["mfa"]
            token_manager = token_service.TokenService(user=user)

            if mfa:
                response = Response(
                    data={"status": "success", "mfa": user.id},
                    status=status.HTTP_200_OK,
                )
                response = token_manager.delete_tokens_from_response(response)
                return token_manager.handle_mfa_cookie(response, action="add")
            else:
                tokens = token_manager.generate_tokens()
                basic_serializer = get_serializer_class(
                    auth_config.basic_account_serializer_class
                )
                email_manager = email_service.EmailService(request=request)
                email_manager.send_login_alert(user.email_address)
                response = token_manager.handle_mfa_cookie(
                    response=Response(
                        data={
                            "status": "success",
                            "access_token": tokens["access_token"],
                            "refresh_token": tokens["refresh_token"],
                            "user": basic_serializer(user).data,
                        }
                    ),
                    action="remove",
                )
                return token_manager.add_tokens_to_response(response, tokens)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.exception(f"Error occurred while logging in. Error: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def mfa_login_view(request):
    """Handle MFA login using a provided MFA or recovery code."""
    # Retrieve MFA cookie with user ID
    user_id = request.COOKIES.get(auth_config.mfa_token_cookie_name, None)
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

    elif mfa_handler.verify_recovery_code(code):
        is_valid = True

    if is_valid:
        token_manager = token_service.TokenService(user=user)
        tokens = token_manager.generate_tokens()
        response = token_manager.add_tokens_to_response(
            response=Response(
                data={
                    "status": "success",
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "user": get_serializer_class(
                        auth_config.basic_account_serializer_class
                    )(user).data,
                }
            ),
            tokens=tokens,
        )
        return token_manager.handle_mfa_cookie(response, action="remove")
    else:
        return Response(
            {"error": "Invalid MFA code or recovery code."},
            status=status.HTTP_400_BAD_REQUEST,
        )
