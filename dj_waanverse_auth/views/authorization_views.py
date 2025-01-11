from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from dj_waanverse_auth.services.token_service import TokenService
from dj_waanverse_auth.services.utils import get_serializer_class
from dj_waanverse_auth.settings import auth_config


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
    refresh_token = request.COOKIES.get(
        auth_config.refresh_token_cookie, None
    ) or request.data.get("refresh_token", None)

    token_service = TokenService(refresh_token=refresh_token)

    if not refresh_token:
        return token_service.delete_tokens_from_response(
            response=Response(
                {"error": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        )

    try:
        tokens = token_service.generate_tokens()

        response = Response(
            data={"access_token": tokens["access_token"]},
            status=status.HTTP_200_OK,
        )
        return token_service.add_tokens_to_response(response, tokens)
    except Exception as e:
        response = Response(
            {"error": str(e)},
            status=status.HTTP_401_UNAUTHORIZED,
        )
        return token_service.delete_tokens_from_response(response)


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
