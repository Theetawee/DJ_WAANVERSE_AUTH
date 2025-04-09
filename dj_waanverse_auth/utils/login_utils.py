from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.services.token_service import TokenService
from dj_waanverse_auth.utils.email_utils import send_login_email
from dj_waanverse_auth.utils.serializer_utils import get_serializer_class


def handle_login(request: object, user: User, mfa: int = 0) -> Response:
    token_manager = TokenService(request=request, user=user)

    if mfa != 0:
        response = Response(
            data={"status": "success", "mfa": user.id},
            status=status.HTTP_200_OK,
        )
        response = token_manager.clear_all_cookies(response)
        return response
    else:
        basic_serializer = get_serializer_class(
            auth_config.basic_account_serializer_class
        )
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

        send_login_email(request, user)
        return response
