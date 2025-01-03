# tokens.py
import logging
from functools import cached_property

from django.utils.timezone import now

from dj_waanverse_auth.settings import auth_config

from .utils import decode_token, encode_token

logger = logging.getLogger(__name__)


class TokenError(Exception):
    pass


class RefreshToken:
    REQUIRED_CLAIMS = {"user_id", "exp", "iat", "iss"}

    def __init__(self, token=None):
        self.token = token
        self._payload = None

        if token:
            try:
                self._payload = decode_token(token)
                self._validate_claims()
            except Exception as e:
                logger.error(f"Token initialization failed: {str(e)}")
                raise TokenError(f"Invalid token: {str(e)}")

    def _validate_claims(self):
        """Validate required claims are present in token"""
        if not all(claim in self._payload for claim in self.REQUIRED_CLAIMS):
            missing = self.REQUIRED_CLAIMS - set(self._payload.keys())
            raise TokenError(f"Missing required claims: {missing}")

    @classmethod
    def for_user(cls, user):
        """Generate a refresh token for a user with error handling"""
        try:
            expiration = now() + auth_config.refresh_token_cookie_max_age
            payload = {
                "user_id": user.id,
                "exp": expiration,
                "iat": now(),
                "iss": auth_config.platform_name,
                "token_type": "refresh",
            }
            token = encode_token(payload)
            return cls(token)
        except Exception as e:
            logger.error(f"Failed to create refresh token: {str(e)}")
            raise TokenError("Could not generate refresh token")

    @cached_property
    def payload(self):
        """Cached access to decoded payload"""
        return self._payload

    @property
    def access_token(self):
        """Generate an access token with caching and validation"""
        if not self._payload:
            logger.error(
                "Attempted to generate access token from invalid refresh token"
            )
            raise TokenError("Refresh token is not valid")

        try:
            expiration = now() + auth_config.access_token_cookie_max_age
            access_payload = {
                "user_id": self._payload["user_id"],
                "exp": expiration,
                "iat": now(),
                "iss": auth_config.platform_name,
                "token_type": "access",
            }
            return encode_token(access_payload)
        except Exception as e:
            logger.error(f"Failed to generate access token: {str(e)}")
            raise TokenError("Could not generate access token")

    @classmethod
    def verify(cls, token):
        """Verify token with detailed error logging"""
        try:
            instance = cls(token)
            return bool(instance.payload)
        except TokenError as e:
            logger.info(f"Token verification failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in token verification: {str(e)}")
            return False

    def __str__(self):
        return self.token or ""

    def __bool__(self):
        return bool(self._payload)
