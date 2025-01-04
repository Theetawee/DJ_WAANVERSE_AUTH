from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dj_waanverse_auth.services.token_service import TokenService
from dj_waanverse_auth.services.utils import get_serializer_class
from dj_waanverse_auth.settings import auth_config


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def refresh_access_token(request):
    refresh_token = request.COOKIES.get("refresh_token", None) or request.data.get(
        "refresh_token", None
    )

    if not refresh_token:
        return Response(
            {"error": "Refresh token is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    token_service = TokenService(refresh_token=refresh_token)

    try:
        # Generate new tokens
        tokens = token_service.generate_tokens()

        # Prepare the response and add the tokens as cookies
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
