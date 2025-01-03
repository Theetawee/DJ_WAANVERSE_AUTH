from django.utils.timezone import now

from dj_waanverse_auth.settings import auth_config

from .utils import decode_token, encode_token


class TokenError(Exception):
    """Custom exception for token-related errors."""

    pass


class RefreshToken:
    """Represents a JWT refresh token, its creation, verification, and access."""

    def __init__(self, token=None):
        self.token = token
        self.payload = None

        if token:
            self.payload = decode_token(token)

    @classmethod
    def for_user(cls, user):
        """Generate a refresh token for a user."""
        expiration = now() + auth_config.refresh_token_cookie_max_age
        payload = {
            "user_id": user.id,
            "exp": expiration,
            "iat": now(),
        }
        token = encode_token(payload)
        return cls(token)

    @property
    def access_token(self):
        """Generate an access token based on the refresh token payload."""
        if not self.payload:
            raise TokenError("Refresh token is not valid.")

        expiration = now() + auth_config.access_token_cookie_max_age
        access_payload = {
            "user_id": self.payload["user_id"],
            "exp": expiration,
            "iat": now(),
        }
        return encode_token(access_payload)

    @staticmethod
    def verify(token):
        """Verify the refresh token."""
        try:
            RefreshToken(token)
            return True
        except TokenError:
            return False

    def __str__(self):
        """Return the string representation of the token."""
        return self.token
