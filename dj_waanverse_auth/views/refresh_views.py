# dj_waanverse_auth/views/refresh_views.py
from __future__ import annotations

from logging import getLogger

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from dj_waanverse_auth.authentication import (
    get_refresh_token,
    enforce_csrf_if_cookie_sourced,
)
from dj_waanverse_auth.utils.security.cookies import (
    build_auth_response,
    clear_auth_cookies,
)
from dj_waanverse_auth.utils.security.tokens import RefreshError, rotate_refresh_token

logger = getLogger(__name__)

GENERIC_REFRESH_ERROR = "Invalid or expired session. Please log in again."


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh_token, source = get_refresh_token(request)

        if not raw_refresh_token:
            return Response(
                {"msg": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enforce_csrf_if_cookie_sourced(
            request, source
        )  # raises PermissionDenied -> 403

        try:
            tokens = rotate_refresh_token(raw_refresh_token)
        except RefreshError as exc:
            logger.info("Refresh rejected: %s", exc)
            response = Response(
                {"msg": GENERIC_REFRESH_ERROR}, status=status.HTTP_401_UNAUTHORIZED
            )
            return clear_auth_cookies(response)

        return build_auth_response(
            request,
            tokens,
            data={"msg": "Token refreshed."},
            status_code=status.HTTP_200_OK,
        )
