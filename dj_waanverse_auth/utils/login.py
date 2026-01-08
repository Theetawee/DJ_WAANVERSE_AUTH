from django.utils import timezone
from dj_waanverse_auth.services.token_service import TokenService
from dj_waanverse_auth.utils.serializer_utils import get_serializer_class
from dj_waanverse_auth import settings as auth_config
from rest_framework.response import Response
from rest_framework import status


def handle_login(request: object, user):
    token_manager = TokenService(request=request, user=user)

    basic_serializer = get_serializer_class(auth_config.basic_account_serializer_class)
    response = Response(
        data={
            "status": "success",
            "user": basic_serializer(user).data,
        },
        status=status.HTTP_200_OK,
    )
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])

    response_data = token_manager.setup_login_cookies(response=response)
    response = response_data["response"]
    tokens = response_data["tokens"]
    response.data["access_token"] = tokens["access_token"]
    response.data["refresh_token"] = tokens["refresh_token"]
    response.data["sid"] = tokens["sid"]

    return response
