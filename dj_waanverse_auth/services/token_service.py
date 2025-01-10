import hashlib
import logging
import uuid

from dj_waanverse_auth.models import UserDevice
from dj_waanverse_auth.security.utils import get_ip_address
from dj_waanverse_auth.settings import auth_config

from .token_classes import RefreshToken, TokenError

logger = logging.getLogger(__name__)


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
        self.DEVICE_ID_COOKIE_NAME = auth_config.device_id_cookie_name
        self.DEVICE_HEADER_NAME = auth_config.device_id_header_name

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

    def __init__(self, request, user=None, refresh_token=None, login_method=None):
        self.user = user
        self.refresh_token = refresh_token
        self.cookie_settings = CookieSettings()
        self._tokens = None
        self.request = request
        self.user_agent = request.headers.get("User-Agent", "")
        self.platform = request.headers.get("Sec-CH-UA-Platform", "Unknown").strip('"')
        self.login_method = login_method

    @property
    def tokens(self):
        """Lazy loading of tokens."""
        if self._tokens is None:
            self._tokens = self.generate_tokens()
        return self._tokens

    def generate_tokens(self):
        """Generates new access and refresh tokens."""
        if not self.user and not self.refresh_token:
            raise ValueError("Either user or refresh_token must be provided")

        try:
            if self.refresh_token:
                refresh = RefreshToken(self.refresh_token)
            else:
                refresh = RefreshToken.for_user(self.user)

            return {
                "refresh_token": str(refresh),
                "access_token": str(refresh.access_token),
            }
        except TokenError as e:
            raise TokenError(f"Failed to generate tokens: {str(e)}")

    def generate_device_id(self) -> str:
        """Generates a unique and secure device identifier."""
        browser = self.user_agent.split(" ")[0] if self.user_agent else "Unknown"

        raw_string = f"{self.user.id}|{self.platform}|{browser}|{uuid.uuid4()}"
        hashed_id = hashlib.sha256(raw_string.encode()).hexdigest()
        return f"{hashed_id[:16]}"

    def setup_login_cookies(self, response):
        """
        Sets up all necessary cookies after successful login.

        Args:
            response: HttpResponse object
            request: HttpRequest object (optional, needed for device ID generation)
            tokens: Dictionary containing access and refresh tokens ie {"access_token": "token", "refresh_token": "token"}

        Returns:
            Dictionary containing:
                - response: HttpResponse with all login-related cookies set
                - tokens: Dictionary with access and refresh tokens
                - device_id: Device ID if generated, None otherwise
        """
        if not self.user:
            raise ValueError("User is required for cookie setup")
        # remove the mfa cookie
        response.delete_cookie(
            self.cookie_settings.MFA_COOKIE_NAME,
            domain=self.cookie_settings.DOMAIN,
            path=self.cookie_settings.PATH,
        )
        try:
            cookie_params = self.cookie_settings.get_cookie_params()
            device_id = None

            tokens = self.tokens
            response.set_cookie(
                self.cookie_settings.REFRESH_COOKIE_NAME,
                tokens["refresh_token"],
                max_age=self.cookie_settings.REFRESH_COOKIE_MAX_AGE,
                **cookie_params,
            )

            response.set_cookie(
                self.cookie_settings.ACCESS_COOKIE_NAME,
                tokens["access_token"],
                max_age=self.cookie_settings.ACCESS_COOKIE_MAX_AGE,
                **cookie_params,
            )

            device_id = self.generate_device_id()
            ip_address = get_ip_address(self.request)
            try:
                new_device = UserDevice.objects.create(
                    device_id=device_id,
                    account=self.user,
                    ip_address=ip_address,
                    user_agent=self.user_agent,
                    login_method=self.login_method,
                )
                new_device.save()

                response.set_cookie(
                    self.cookie_settings.DEVICE_ID_COOKIE_NAME,
                    device_id,
                    max_age=self.cookie_settings.REFRESH_COOKIE_MAX_AGE,
                    **cookie_params,
                )
            except Exception as e:
                logger.error(f"Failed to set device cookie: {str(e)}")
                raise TokenError(f"Failed to set device cookie: {str(e)}")

            return {"response": response, "tokens": tokens, "device_id": device_id}
        except Exception as e:
            logger.error(f"Failed to set login cookies: {str(e)}")
            raise

    def clear_all_cookies(self, response):
        """
        Removes all authentication-related cookies.

        Args:
            response: HttpResponse object

        Returns:
            HttpResponse with all auth cookies removed
        """
        cookie_params = {
            "domain": self.cookie_settings.DOMAIN,
            "path": self.cookie_settings.PATH,
        }

        cookies_to_remove = [
            self.cookie_settings.REFRESH_COOKIE_NAME,
            self.cookie_settings.ACCESS_COOKIE_NAME,
            self.cookie_settings.DEVICE_ID_COOKIE_NAME,
            self.cookie_settings.MFA_COOKIE_NAME,
        ]

        for cookie_name in cookies_to_remove:
            response.delete_cookie(cookie_name, **cookie_params)

        device_id = response.cookies.get(self.cookie_settings.DEVICE_ID_COOKIE_NAME)
        if device_id:
            UserDevice.objects.filter(device_id=device_id).delete()

        return response

    def handle_mfa_state(self, response, action="add", preserve_other_cookies=True):
        """
        Manages MFA-related cookies while optionally preserving other authentication cookies.

        Args:
            response: HttpResponse object
            action: str, either 'add' or 'remove'
            preserve_other_cookies: bool, whether to keep other auth cookies

        Returns:
            Dictionary containing:
                - response: HttpResponse with updated cookies
                - mfa_token: MFA token if action is 'add', None if 'remove'
        """
        if action not in ["add", "remove"]:
            raise ValueError("Invalid action for MFA cookie handling")

        cookie_params = self.cookie_settings.get_cookie_params()
        mfa_token = None

        if action == "add":
            if not self.user:
                raise ValueError("User is required for MFA cookie setup")

            mfa_token = str(self.user.id)
            response.set_cookie(
                self.cookie_settings.MFA_COOKIE_NAME,
                mfa_token,
                max_age=self.cookie_settings.MFA_COOKIE_MAX_AGE,
                **cookie_params,
            )
        else:
            response.delete_cookie(
                self.cookie_settings.MFA_COOKIE_NAME,
                domain=self.cookie_settings.DOMAIN,
                path=self.cookie_settings.PATH,
            )

            if not preserve_other_cookies:
                response = self.clear_all_cookies(response)

        return {"response": response, "mfa_token": mfa_token}

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
