import base64
import hashlib
import secrets
from urllib.parse import urlencode

import requests
from django.contrib.auth import get_user_model

from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.models import GoogleStateToken

User = get_user_model()


class GoogleOAuth:
    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

    DEFAULT_SCOPE = [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
    ]

    def __init__(self, request=None):
        """Initialize Google OAuth handler with optional request object."""
        self.client_id = auth_config.google_client_id
        self.client_secret = auth_config.google_client_secret
        self.redirect_uri = auth_config.google_redirect_uri
        self.request = request

    def get_authorization_url(self, state=None, prompt=None):
        """
        Generate the Google OAuth 2.0 authorization URL.

        Args:
            state (str, optional): A random string to prevent CSRF. If None, one will be generated.
            prompt (str, optional): Whether to prompt the user for consent. Options: None, 'consent', 'select_account'

        Returns:
            tuple: (authorization_url, state)
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        # Generate PKCE code verifier and challenge
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = self._generate_code_challenge(code_verifier)

        GoogleStateToken.objects.create(state=state, code_verifier=code_verifier)

        # Build authorization parameters
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.DEFAULT_SCOPE),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
        }

        if prompt:
            params["prompt"] = prompt

        # Build the authorization URL
        auth_url = f"{self.AUTHORIZATION_URL}?{urlencode(params)}"
        return auth_url, state, code_verifier

    def exchange_code_for_token(self, code, code_verifier):
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code (str): The authorization code from Google
            code_verifier (str, optional): PKCE code verifier used in authorization request

        Returns:
            dict: The token response containing access_token, refresh_token, etc.
        """

        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        # Add code_verifier if available
        if code_verifier:
            token_data["code_verifier"] = code_verifier

        # Make the token request
        response = requests.post(self.TOKEN_URL, data=token_data)

        # Raise exception if request failed
        response.raise_for_status()

        # Return token response

        return response.json()

    def get_user_info(self, access_token):
        """
        Get user information from Google using the access token.

        Args:
            access_token (str): The OAuth access token

        Returns:
            dict: User information from Google
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(self.USER_INFO_URL, headers=headers)
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self, refresh_token):
        """
        Refresh the access token using the refresh token.

        Args:
            refresh_token (str): The OAuth refresh token

        Returns:
            dict: New token information
        """
        refresh_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        response = requests.post(self.TOKEN_URL, data=refresh_data)
        response.raise_for_status()
        return response.json()

    def authenticate_or_create_user(self, user_info):
        """
        Authenticate an existing user or create a new one based on Google user info.

        Args:
            user_info (dict): User information from Google

        Returns:
            tuple: (user, created) where user is the User instance and created is a boolean
        """
        email_address = user_info.get("email")
        if not email_address:
            raise ValueError("Email not provided by Google")

        # Check if the user exists
        try:
            user = User.objects.get(email_address=email_address)
            if user.email_verified is False:
                user.email_verified = user_info.get("email_verified", False)
                user.save()
            created = False
        except User.DoesNotExist:

            user = User.objects.create_user(
                email_address=email_address,
                email_verified=True,
            )
            user.is_active = True
            user.save()
            created = True

        return user, created

    def _generate_code_challenge(self, code_verifier):
        """
        Generate a PKCE code challenge from the code verifier.

        Args:
            code_verifier (str): The PKCE code verifier

        Returns:
            str: The code challenge
        """
        # Create SHA-256 hash of code_verifier
        code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        # Base64 encode the hash
        code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
        # Remove padding
        code_challenge = code_challenge.replace("=", "")
        return code_challenge
