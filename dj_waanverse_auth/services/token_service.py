import logging

from rest_framework.response import Response

from dj_waanverse_auth import settings
from dj_waanverse_auth.utils.session_utils import create_session

from .token_classes import RefreshToken, TokenError

logger = logging.getLogger(__name__)


class CookieSettings:
    """Configuration for cookie settings with enhanced security features."""

    def __init__(self):
        self.HTTPONLY = settings.cookie_httponly
        self.SECURE = settings.cookie_secure
        self.SAME_SITE = settings.cookie_samesite
        self.ACCESS_COOKIE_NAME = settings.access_token_cookie
        self.REFRESH_COOKIE_NAME = settings.refresh_token_cookie
        self.ACCESS_COOKIE_MAX_AGE = int(
            (settings.access_token_cookie_max_age).total_seconds()
        )
        self.REFRESH_COOKIE_MAX_AGE = int(
            (settings.refresh_token_cookie_max_age).total_seconds()
        )
        self.DOMAIN = settings.cookie_domain
        self.PATH = settings.cookie_path

    def get_cookie_params(self):
        """Returns common cookie parameters as a dictionary."""
        return {
            "httponly": self.HTTPONLY,
            "secure": self.SECURE,
            "samesite": self.SAME_SITE,
            "domain": self.DOMAIN,
            "path": self.PATH,
        }


class TokenService:
    """Service for handling JWT token operations with enhanced security and functionality."""

    def __init__(self, request, user=None, refresh_token=None):
        self.user = user
        self.refresh_token = refresh_token
        self.cookie_settings = CookieSettings()
        self._tokens = None
        self.request = request
        self.user_agent = request.headers.get("User-Agent", "")
        self.platform = request.headers.get("Sec-CH-UA-Platform", "Unknown").strip('"')
        self.is_refresh = bool(refresh_token)

    @property
    def tokens(self):
        """Lazy loading of tokens."""
        if self._tokens is None:
            self._tokens = self.generate_tokens()
        return self._tokens

    def generate_tokens(self):
        """
        Generates tokens based on the context:
        - If refresh_token is provided, only generates new access token
        - If user is provided, generates both new access and refresh tokens
        """
        if not self.user and not self.refresh_token:
            raise ValueError("Either user or refresh_token must be provided")

        try:
            if self.refresh_token:
                refresh = RefreshToken(self.refresh_token)
                return {
                    "refresh_token": self.refresh_token,
                    "access_token": str(refresh.access_token),
                }
            else:

                session_id = create_session(user=self.user, request=self.request)
                refresh = RefreshToken.for_user(self.user, session_id=session_id)
                return {
                    "refresh_token": str(refresh),
                    "access_token": str(refresh.access_token),
                    "sid": session_id,
                }
        except TokenError as e:
            raise TokenError(f"Failed to generate tokens: {str(e)}")

    def setup_login_cookies(self, response):
        """
        Sets up cookies based on the context:
        - For token refresh: Only updates access token cookie
        - For new login: Sets up all cookies and registers device
        """
        try:
            cookie_params = self.cookie_settings.get_cookie_params()
            tokens = self.tokens
            # Always set the new access token
            response.set_cookie(
                self.cookie_settings.ACCESS_COOKIE_NAME,
                tokens["access_token"],
                max_age=self.cookie_settings.ACCESS_COOKIE_MAX_AGE,
                **cookie_params,
            )

            if not self.is_refresh:
                # Set refresh token cookie
                response.set_cookie(
                    self.cookie_settings.REFRESH_COOKIE_NAME,
                    tokens["refresh_token"],
                    max_age=self.cookie_settings.REFRESH_COOKIE_MAX_AGE,
                    **cookie_params,
                )

            return {"response": response, "tokens": tokens}
        except Exception as e:
            logger.error(f"Failed to set login cookies: {str(e)}")
            raise

    def clear_all_cookies(self, response: Response) -> Response:
        """Removes all authentication-related cookies."""
        cookie_params = {
            "domain": self.cookie_settings.DOMAIN,
            "path": self.cookie_settings.PATH,
        }

        cookies_to_remove = [
            self.cookie_settings.REFRESH_COOKIE_NAME,
            self.cookie_settings.ACCESS_COOKIE_NAME,
        ]

        for cookie_name in cookies_to_remove:
            response.delete_cookie(cookie_name, **cookie_params)

        return response

    @staticmethod
    def get_token_from_cookies(request, token_type="access"):
        """Retrieves token from cookies."""
        cookie_name = (
            CookieSettings().ACCESS_COOKIE_NAME
            if token_type == "access"
            else CookieSettings().REFRESH_COOKIE_NAME
        )
        return request.COOKIES.get(cookie_name)

    def verify_token(self, token):
        """Verifies if a token is valid."""
        try:
            RefreshToken(token)
            return True
        except TokenError:
            return False
