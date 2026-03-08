from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from dj_waanverse_auth import settings as auth_config
from rest_framework.response import Response
import urllib.parse
import requests as py_requests

from rest_framework.views import APIView
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from dj_waanverse_auth.utils.login import handle_login

User = get_user_model()


User = get_user_model()


@api_view(["GET"])
@permission_classes([AllowAny])
def google_oauth_link(request):

    if (
        auth_config.google_client_id is None
        or auth_config.google_redirect_uri is None
        or auth_config.google_client_secret is None
    ):
        return Response(
            {
                "error": "Google Client ID, Secret, and Redirect URI must be set in AUTH_CONFIG"
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    params = {
        "client_id": auth_config.google_client_id,
        "redirect_uri": auth_config.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }

    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    )
    return Response({"url": url}, status=status.HTTP_200_OK)


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    google_client_id: str = auth_config.google_client_id
    google_client_secret: str = auth_config.google_client_secret
    google_redirect_uri: str = auth_config.google_redirect_uri

    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response(
                {"error": "No code provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not all(
            [self.google_client_id, self.google_client_secret, self.google_redirect_uri]
        ):
            raise Exception("Google Client ID, Secret, and Redirect URI must be set")

        try:
            token_data = self.exchange_code_for_tokens(code)
            id_token_str = token_data.get("id_token")

            if not id_token_str:
                return Response(
                    {"error": "Failed to obtain ID token"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            id_info = self.verify_id_token(id_token_str)
            email = id_info["email"]
            name = id_info.get("name")

            user = self.get_or_create_user(email=email, name=name, id_info=id_info)

            response = handle_login(request, user)

            return response

        except Exception as e:
            print(e, "GoogleAuthView error")
            return Response(
                {"error": "Invalid token or code"}, status=status.HTTP_400_BAD_REQUEST
            )

    # --- Helper methods you can override ---

    def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange authorization code for ID token and access token."""
        res = py_requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": self.google_client_id,
                "client_secret": self.google_client_secret,
                "redirect_uri": self.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        res.raise_for_status()
        return res.json()

    def verify_id_token(self, id_token_str: str) -> dict:
        """Verify the ID token with Google."""
        return google_id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), self.google_client_id
        )

    def get_or_create_user(self, email: str, name: str, id_info: dict):
        """
        Create a new user or retrieve an existing one based on the email.

        This method is called after a successful Google authentication.
        Subclasses can override this method to customize user creation,
        for example to:

        - Populate additional fields (profile picture, username, etc.)
        - Assign default groups or permissions
        - Link the user to other models in your system

        Parameters:
        - email (str): The user's verified email from Google.
        - name (str): The user's full name from Google.
        - id_info (dict): The full decoded ID token payload returned by Google.
        Contains fields like 'email_verified', 'sub' (Google user ID), 'picture', etc.

        Returns:
        - user (User): The Django user instance created or retrieved.
        """

        user, created = User.objects.get_or_create(email=email, defaults={"name": name})
        if created:
            user.name = name
            user.save()
        return user
