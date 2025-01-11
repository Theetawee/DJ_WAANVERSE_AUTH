import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from dj_waanverse_auth.services.token_service import TokenService
from dj_waanverse_auth.services.utils import get_serializer_class
from dj_waanverse_auth.settings import auth_config

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def home_page(request):
    return Response(
        data={"status": "success", "message": "Welcome to Dj Waanverse Auth"},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_access_token(request):
    """
    View to refresh the access token using a valid refresh token.
    The refresh token can be provided either in cookies or request body.
    """
    # Get refresh token from cookie or request body
    refresh_token = request.COOKIES.get(
        auth_config.refresh_token_cookie
    ) or request.data.get("refresh_token")

    if not refresh_token:
        response = Response(
            {
                "error": "Refresh token is required.",
                "error_code": "REFRESH_TOKEN_REQUIRED",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
        return TokenService(request=request).clear_all_cookies(response)

    token_service = TokenService(request=request, refresh_token=refresh_token)

    try:
        if not token_service.verify_token(refresh_token):
            return Response(
                {
                    "error": "Invalid refresh token.",
                    "error_code": "INVALID_REFRESH_TOKEN",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        response = Response(status=status.HTTP_200_OK)

        # Setup cookies with only access token being refreshed
        response_data = token_service.setup_login_cookies(response=response)
        response = response_data["response"]

        # Include the new access token in response data
        response.data = {
            "message": "Token refreshed successfully",
            "access_token": response_data["tokens"]["access_token"],
        }

        return response

    except Exception as e:
        logger.warning(f"Invalid refresh token attempt: {str(e)}")
        response = Response(
            {
                "error": "Invalid refresh token.",
                "error_code": "INVALID_REFRESH_TOKEN",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )
        return token_service.clear_all_cookies(response)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def authenticated_user(request):
    basic_account_serializer = get_serializer_class(
        auth_config.basic_account_serializer_class
    )

    return Response(
        data=basic_account_serializer(request.user).data,
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    token_manager = TokenService()
    return token_manager.delete_tokens_from_response(
        Response(status=status.HTTP_200_OK, data={"status": "success"})
    )
