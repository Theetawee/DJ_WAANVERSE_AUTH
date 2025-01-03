from dj_waanverse_auth.settings import auth_config

from .token_classes import RefreshToken, TokenError


class CookieSettings:
    """Configuration for cookie settings with enhanced security features."""

    def __init__(self):
        self.HTTPONLY = auth_config.cookie_httponly
        self.SECURE = auth_config.cookie_secure
        self.SAME_SITE = auth_config.cookie_samesite
        self.ACCESS_COOKIE_NAME = auth_config.access_token_cookie
        self.REFRESH_COOKIE_NAME = auth_config.refresh_token_cookie
        self.MFA_COOKIE_NAME = auth_config.mfa_token_cookie_name
        self.ACCESS_COOKIE_MAX_AGE = int(
            (auth_config.access_token_cookie_max_age).total_seconds()
        )
        self.REFRESH_COOKIE_MAX_AGE = int(
            (auth_config.refresh_token_cookie_max_age).total_seconds()
        )
        self.MFA_COOKIE_MAX_AGE = int(
            (auth_config.mfa_token_cookie_max_age).total_seconds()
        )
        self.DOMAIN = auth_config.cookie_domain
        self.PATH = auth_config.cookie_path

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

    def __init__(self, user=None, refresh_token=None):
        self.user = user
        self.refresh_token = refresh_token
        self.cookie_settings = CookieSettings()
        self._tokens = None

    @property
    def tokens(self):
        """Lazy loading of tokens."""
        if self._tokens is None:
            self._tokens = self.generate_tokens()
        return self._tokens

    def generate_tokens(self):
        """Generates new access and refresh tokens and optionally updates the response with cookies."""
        if not self.user and not self.refresh_token:
            raise ValueError("Either user or refresh_token must be provided")

        try:
            if self.refresh_token:
                refresh = RefreshToken(self.refresh_token)
            else:
                refresh = RefreshToken.for_user(self.user)

            tokens = {
                "refresh_token": str(refresh),
                "access_token": str(refresh.access_token),
            }

            return tokens
        except TokenError as e:
            raise TokenError(f"Failed to generate tokens: {str(e)}")

    def add_tokens_to_response(self, response, tokens):
        """Adds tokens as secure cookies to the response."""
        cookie_params = self.cookie_settings.get_cookie_params()

        # Set refresh token cookie
        response.set_cookie(
            self.cookie_settings.REFRESH_COOKIE_NAME,
            tokens["refresh_token"],
            max_age=self.cookie_settings.REFRESH_COOKIE_MAX_AGE,
            **cookie_params,
        )

        # Set access token cookie
        response.set_cookie(
            self.cookie_settings.ACCESS_COOKIE_NAME,
            tokens["access_token"],
            max_age=self.cookie_settings.ACCESS_COOKIE_MAX_AGE,
            **cookie_params,
        )

        return response

    def delete_tokens_from_response(self, response):
        """Removes token cookies from the response."""
        response.delete_cookie(
            self.cookie_settings.REFRESH_COOKIE_NAME,
            domain=self.cookie_settings.DOMAIN,
            path=self.cookie_settings.PATH,
        )
        response.delete_cookie(
            self.cookie_settings.ACCESS_COOKIE_NAME,
            domain=self.cookie_settings.DOMAIN,
            path=self.cookie_settings.PATH,
        )
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

    def handle_mfa_cookie(self, response):
        """
        Add a cookie containing the user ID if MFA is enabled.
        """
        from dj_waanverse_auth.services.mfa_service import MFAHandler

        mfa_handler = MFAHandler(self.user)
        cookie_params = self.cookie_settings.get_cookie_params()

        if mfa_handler.is_mfa_enabled():
            mfa_id = str(mfa_handler.mfa.id)

            response.set_cookie(
                self.cookie_settings.MFA_COOKIE_NAME,
                mfa_id,
                max_age=self.cookie_settings.MFA_COOKIE_MAX_AGE,
                **cookie_params,
            )
        else:
            response.delete_cookie(
                self.cookie_settings.MFA_COOKIE_NAME,
                domain=self.cookie_settings.DOMAIN,
                path=self.cookie_settings.PATH,
            )
        return response
