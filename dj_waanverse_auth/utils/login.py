from django.utils import timezone
from dj_waanverse_auth.services.token_service import TokenService
from dj_waanverse_auth.utils.serializer_utils import get_serializer_class
from dj_waanverse_auth import settings as auth_config
from rest_framework.response import Response
from rest_framework import status
from dj_waanverse_auth.models import AccessCode
from django.contrib.auth import get_user_model

Account = get_user_model()


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


def verify_code_flow(request, email, code):
    if email not in auth_config.testing_email_addresses or not auth_config.is_testing:
        access_instance = AccessCode.objects.filter(
            code=code, email_address=email
        ).first()
        if not access_instance or access_instance.is_expired():
            return Response(
                {"detail": "Invalid or expired code."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    account = Account.objects.filter(email_address=email).first()
    if not account:
        account = Account.objects.create_user(email_address=email)
    if not account.email_verified or not account.is_active:
        account.email_verified = True
        account.is_active = True
        account.save(update_fields=["email_verified", "is_active"])

    # Login and return response (e.g., tokens or session)
    response = handle_login(request, account)

    # Delete used code
    if email not in auth_config.testing_email_addresses or not auth_config.is_testing:
        access_instance.delete()

    return response
