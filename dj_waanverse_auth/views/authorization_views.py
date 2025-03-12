import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from dj_waanverse_auth.config.settings import auth_config
from dj_waanverse_auth.models import UserSession
from dj_waanverse_auth.serializers.authorization_serializer import SessionSerializer
from dj_waanverse_auth.serializers.client_hints_serializers import ClientInfoSerializer
from dj_waanverse_auth.services.mfa_service import MFAHandler
from dj_waanverse_auth.services.session_utils import revoke_session
from dj_waanverse_auth.services.token_service import TokenService
from dj_waanverse_auth.services.utils import decode_token, get_serializer_class

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_device_info(request):
    client_info = ClientInfoSerializer(request.client_info)

    return Response(client_info.data, status=status.HTTP_200_OK)


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
@permission_classes([IsAuthenticated])
def logout_view(request):
    access_token = request.COOKIES.get(auth_config.access_token_cookie)

    if not access_token:
        access_token = request.data.get("access_token")

    if not access_token:
        return Response(
            {"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST
        )

    payload = decode_token(access_token)
    session_id = payload.get("sid")

    if not session_id:
        return Response(
            {"error": "Session ID missing from token"},
            status=status.HTTP_400_BAD_REQUEST,
        )

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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def grant_access_view(request):
    method = request.data.get("method")
    if method not in {"password", "mfa", "password-mfa"}:
        return Response(
            {"msg": "Unsupported method"}, status=status.HTTP_400_BAD_REQUEST
        )

    user = request.user

    # Password authentication
    if "password" in method:
        password = request.data.get("password")
        if not password:
            return Response(
                {"msg": "Password is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(password):
            return Response(
                {"msg": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED
            )

    # MFA authentication
    if "mfa" in method:
        mfa_code = request.data.get("mfa_code")
        if not mfa_code:
            return Response(
                {"msg": "MFA code is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            mfa_handler = MFAHandler(user)
            if not mfa_handler.verify_token(mfa_code):
                return Response(
                    {"msg": "Invalid MFA code"}, status=status.HTTP_401_UNAUTHORIZED
                )
        except Exception as e:
            logger.error(f"MFA verification failed: {str(e)}")
            return Response(
                {"msg": "MFA verification error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return Response({"msg": "Access granted"}, status=status.HTTP_200_OK)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_account(request):
    user = request.user
    serializer_class = get_serializer_class(auth_config.update_account_serializer)
    serializer = serializer_class(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(data={"msg": "updated"}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
