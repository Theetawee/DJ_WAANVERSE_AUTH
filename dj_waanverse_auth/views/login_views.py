from __future__ import annotations

from logging import getLogger

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from dj_waanverse_auth.utils import identifiers as identifier_utils
from dj_waanverse_auth.utils.security.cookies import build_auth_response
from dj_waanverse_auth.utils.security.tokens import issue_tokens_for_account
from dj_waanverse_auth.utils.security.turnstile import verify_turnstile_token
from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.throttles import LoginIdentifierThrottle, LoginIPThrottle

logger = getLogger(__name__)

Account = get_user_model()

GENERIC_LOGIN_ERROR = "Invalid identifier or password."
MAX_IDENTIFIER_LENGTH = 255
MAX_PASSWORD_LENGTH = 128


# dj_waanverse_auth/views/login_views.py


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginIdentifierThrottle, LoginIPThrottle]

    def post(self, request):
        identifier = request.data.get("identifier")
        password = request.data.get("password")

        if not isinstance(identifier, str) or not identifier.strip():
            return Response(
                {"msg": "Identifier is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not isinstance(password, str) or not password:
            return Response(
                {"msg": "Password is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        if (
            len(identifier) > MAX_IDENTIFIER_LENGTH
            or len(password) > MAX_PASSWORD_LENGTH
        ):
            return Response(
                {"msg": "Invalid request payload."}, status=status.HTTP_400_BAD_REQUEST
            )

        if auth_config.turnstile_enabled:
            turnstile_error = self._validate_turnstile(request)
            if turnstile_error is not None:
                return turnstile_error

        identifier = identifier.strip()

        identifier_type = identifier_utils.get_identifier_type(identifier)

        if identifier_type is None:
            Account().set_password(password)
            return Response(
                {"msg": GENERIC_LOGIN_ERROR}, status=status.HTTP_400_BAD_REQUEST
            )

        account = self._get_account(identifier_type, identifier)

        if account is None:
            Account().set_password(password)
            return Response(
                {"msg": GENERIC_LOGIN_ERROR}, status=status.HTTP_400_BAD_REQUEST
            )

        if not account.check_password(password):
            return Response(
                {"msg": GENERIC_LOGIN_ERROR}, status=status.HTTP_400_BAD_REQUEST
            )

        if not account.is_active:
            return Response(
                {
                    "msg": "Please verify your account before logging in.",
                    "action": "verify",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        tokens = issue_tokens_for_account(account, request=request)

        return build_auth_response(
            request,
            tokens,
            data={"msg": "Login successful."},
            status_code=status.HTTP_200_OK,
        )

    def _validate_turnstile(self, request):
        token = request.data.get("turnstile_token")
        if not isinstance(token, str):
            token = None

        if not verify_turnstile_token(
            token, remote_ip=getattr(request, "ip_address", None)
        ):
            return Response(
                {"msg": "Turnstile verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def _get_account(self, identifier_type, identifier):
        if identifier_type == "phone":
            try:
                phone_number, _ = identifier_utils.normalize_phone(identifier)
            except ValueError:
                return None
            return Account.objects.filter(phone_number=phone_number).first()

        if identifier_type == "email":
            return Account.objects.filter(
                email_address__iexact=identifier.lower()
            ).first()

        return None
