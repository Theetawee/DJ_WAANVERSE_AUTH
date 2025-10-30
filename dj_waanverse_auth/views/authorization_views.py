import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from dj_waanverse_auth.config.settings import auth_config
from dj_waanverse_auth.models import UserSession
from dj_waanverse_auth.serializers import SessionSerializer
from dj_waanverse_auth.services.token_service import TokenService
from dj_waanverse_auth.utils.serializer_utils import get_serializer_class
from dj_waanverse_auth.utils.session_utils import revoke_session

User = get_user_model()
logger = logging.getLogger(__name__)


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
        return response
        # return token_service.clear_all_cookies(response)


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
def logout_view(request, session_id):
    try:
        revoke_session(session_id=session_id)
    except UserSession.DoesNotExist:
        return Response(
            {"error": "Session not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to deactivate session: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    token_manager = TokenService(request=request)

    return token_manager.clear_all_cookies(
        Response(
            status=status.HTTP_200_OK,
            data={"status": "success", "session_id": session_id},
        )
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_sessions(request):
    user = request.user
    sessions = UserSession.objects.filter(account=user)
    serializer = SessionSerializer(sessions, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([AllowAny])
def delete_user_session(request, session_id):
    try:
        session = UserSession.objects.get(id=session_id)
        session.delete()
        return Response({"status": "success"}, status=status.HTTP_200_OK)
    except UserSession.DoesNotExist:
        return Response(
            {"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to delete session: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
