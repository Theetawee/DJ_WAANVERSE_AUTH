import logging
from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions
from rest_framework.request import Request
from rest_framework.response import Response

from dj_waanverse_auth.config.settings import auth_config
from dj_waanverse_auth.utils.session_utils import validate_session
from dj_waanverse_auth.utils.token_utils import decode_token

logger = logging.getLogger(__name__)
User = get_user_model()


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Production-ready JWT authentication class for Django REST Framework.
    Supports header and cookie-based tokens with caching, logging, and security features.
    """

    COOKIE_NAME = auth_config.access_token_cookie

    def authenticate(self, request: Request) -> Optional[Tuple]:
        token = self._get_token_from_request(request)

        # Short-circuit if no token (e.g., login/register requests)
        if not token:
            return None

        try:
            payload = self._decode_token(token)

            if not validate_session(payload.get("sid")):
                self._mark_cookie_for_deletion(request)
                raise exceptions.AuthenticationFailed("identity_error")

            user = self._get_user_from_payload(payload=payload, request=request)
            return user, token

        except exceptions.AuthenticationFailed as e:
            logger.warning(f"Authentication failed: {str(e)}")
            self._mark_cookie_for_deletion(request)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {str(e)}")
            self._mark_cookie_for_deletion(request)
            raise exceptions.AuthenticationFailed("Authentication failed")

    def _mark_cookie_for_deletion(self, request) -> None:
        """
        Mark auth cookies for deletion via request.META
        """
        cookies_to_delete = [
            auth_config.access_token_cookie,
            auth_config.refresh_token_cookie,
        ]
        request.META["HTTP_X_COOKIES_TO_DELETE"] = ",".join(cookies_to_delete)

    @staticmethod
    def delete_marked_cookies(response: Response, request: Request) -> Response:
        """
        Delete any cookies marked during authentication
        """
        cookies_header = request.META.get("HTTP_X_COOKIES_TO_DELETE", "")
        cookies_to_delete = cookies_header.split(",") if cookies_header else []

        for cookie_name in cookies_to_delete:
            response.delete_cookie(
                cookie_name,
                domain=auth_config.cookie_domain,
                path=auth_config.cookie_path,
                samesite=auth_config.cookie_samesite,
            )

        return response

    def _get_token_from_request(self, request) -> Optional[str]:
        """
        Extract token from Authorization header or cookies
        """
        token = None

        # Header first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        # Fallback to cookie
        if not token and self.COOKIE_NAME in request.COOKIES:
            token = request.COOKIES.get(self.COOKIE_NAME)

        # Sanitize
        if token:
            token = self._sanitize_token(token)

        return token

    def _sanitize_token(self, token: str) -> str:
        if not isinstance(token, str):
            raise exceptions.AuthenticationFailed("Invalid token format")
        token = token.strip()
        if len(token) > 2000:
            raise exceptions.AuthenticationFailed("Token exceeds maximum length")
        return token

    def _decode_token(self, token: str) -> dict:
        return decode_token(token)

    def _get_user_from_payload(self, payload: dict, request: Request):
        """
        Retrieve and validate user from token payload
        """
        user_id = payload.get("id")
        if not user_id:
            raise exceptions.AuthenticationFailed("Invalid token payload")

        try:
            user = User.objects.get(id=user_id, is_active=True)
            self._validate_user(user, payload)
            return user
        except User.DoesNotExist:
            logger.warning(f"User {user_id} from token not found or inactive")
            raise exceptions.AuthenticationFailed(
                "user_not_found", code="user_not_found"
            )

    def _validate_user(self, user, payload: dict):
        """
        Extra validation, e.g., password change
        """
        if payload.get("iat"):
            password_changed = getattr(user, "password_last_updated", None)
            if password_changed and password_changed.timestamp() > payload["iat"]:
                raise exceptions.AuthenticationFailed("Password has been changed")

    def authenticate_header(self, request):
        return 'Bearer realm="api"'
