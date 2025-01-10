import logging

from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions
from rest_framework.request import Request

from dj_waanverse_auth.services.utils import decode_token
from dj_waanverse_auth.settings import auth_config

logger = logging.getLogger(__name__)
User = get_user_model()


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Production-ready JWT authentication class for Django REST Framework.
    Supports both header and cookie-based token authentication with caching,
    comprehensive logging, and enhanced security features.
    """

    ALGORITHM = "RS256"
    PUBLIC_KEY_PATH = auth_config.public_key_path
    HEADER_NAME = auth_config.header_name
    COOKIE_NAME = auth_config.access_token_cookie
    USER_ID_CLAIM = auth_config.user_id_claim
    TOKEN_CACHE_TTL = auth_config.token_cache_ttl
    CACHE_PREFIX = auth_config.cache_prefix

    def __init__(self):
        if not self.PUBLIC_KEY_PATH:
            raise exceptions.AuthenticationFailed(
                "JWT_PUBLIC_KEY_PATH must be set in Dj Waanverse Auth settings"
            )
        self._public_key = None

    def authenticate(self, request: Request):
        """
        Main authentication method that handles the token validation process.
        Returns a tuple of (user, token) if authentication is successful.
        """
        try:
            token = self._get_token_from_request(request)
            if not token:
                return None

            payload = self._decode_token(token)
            user = self._get_user_from_payload(payload=payload, request=request)

            return user, token

        except exceptions.AuthenticationFailed as e:
            logger.warning(f"Authentication failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {str(e)}")
            raise exceptions.AuthenticationFailed("Authentication failed")

    def _get_token_from_request(self, request):
        """
        Extract token from request headers or cookies with enhanced security checks.
        """
        token = request.headers.get(self.HEADER_NAME)

        if not token and self.COOKIE_NAME in request.COOKIES:
            if not request.is_secure():
                logger.warning("Cookie token accessed over non-HTTPS connection")
            token = request.COOKIES.get(self.COOKIE_NAME)

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
        user_id = payload.get(self.USER_ID_CLAIM)
        if not user_id:
            raise exceptions.AuthenticationFailed("Invalid token payload")

        try:
            user = User.objects.get(id=user_id, is_active=True)

            self._validate_user(user, payload)
            return user

        except User.DoesNotExist:
            logger.warning(f"User {user_id} from token not found or inactive")
            raise exceptions.AuthenticationFailed(
                "User not found or inactive", code="user_not_found"
            )

    def _validate_user(self, user, payload):
        """
        Additional user validation checks.
        """
        if payload.get("iat"):
            password_changed = getattr(
                user, auth_config.password_changed_field_name, None
            )
            if password_changed and password_changed.timestamp() > payload["iat"]:
                raise exceptions.AuthenticationFailed("Password has been changed")

    def authenticate_header(self, request):
        """
        Return string to be used as the value of the WWW-Authenticate header.
        """
        return 'Bearer realm="api"'
