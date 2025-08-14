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
    Supports both header and cookie-based token authentication with caching,
    comprehensive logging, and enhanced security features.
    """

    COOKIE_NAME = auth_config.access_token_cookie

    def authenticate(self, request: Request) -> Optional[Tuple]:
        try:
            token = self._get_token_from_request(request)
            if not token:
                return None

            payload = self._decode_token(token)

            if not validate_session(payload["sid"]):
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
        Mark the authentication cookies for deletion using request.META.
        """
        cookies_to_delete = [
            auth_config.access_token_cookie,
            auth_config.refresh_token_cookie,
        ]
        request.META["HTTP_X_COOKIES_TO_DELETE"] = ",".join(cookies_to_delete)

    @staticmethod
    def delete_marked_cookies(response: Response, request: Request) -> Response:
        """
        Delete any cookies that were marked for deletion during authentication.
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

    def _get_token_from_request(self, request):
        """
        Extract token from request Authorization header or cookies with enhanced security checks.
        """
        token = None

        # Try extracting token from the Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        # If token is not in the Authorization header, check cookies
        if not token and self.COOKIE_NAME in request.COOKIES:
            token = request.COOKIES.get(self.COOKIE_NAME)

        # Sanitize the token if it was found
        if token:
            token = self._sanitize_token(token)

        return token

    def _sanitize_token(self, token):
        """
        Sanitize and validate token format before processing.
        """
        if not isinstance(token, str):
            raise exceptions.AuthenticationFailed("Invalid token format")

        token = token.strip()
        if len(token) > 2000:
            raise exceptions.AuthenticationFailed("Token exceeds maximum length")

        return token

    def _decode_token(self, token):
        return decode_token(token)

    def _get_user_from_payload(self, payload, request):
        """
        Retrieve and validate user from token payload.
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

    def _validate_user(self, user, payload):
        """
        Additional user validation checks.
        """
        if payload.get("iat"):
            password_changed = getattr(user, "password_last_updated", None)
            if password_changed and password_changed.timestamp() > payload["iat"]:
                raise exceptions.AuthenticationFailed("Password has been changed")

    def authenticate_header(self, request):
        """
        Return string to be used as the value of the WWW-Authenticate header.
        """
        return 'Bearer realm="api"'
