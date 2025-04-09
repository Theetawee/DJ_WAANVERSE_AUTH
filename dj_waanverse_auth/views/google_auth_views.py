from logging import getLogger

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.google_auth import GoogleOAuth
from dj_waanverse_auth.services.token_service import TokenService
from dj_waanverse_auth.services.utils import get_serializer_class

logger = getLogger(__name__)


def google_login(request):
    # Initialize Google OAuth handler
    google_oauth = GoogleOAuth(request)

    # Get authorization URL and store state in session
    auth_url, _, _ = google_oauth.get_authorization_url()

    # Redirect to Google authorization endpoint
    return HttpResponseRedirect(auth_url)


def google_callback(request):
    # Get authorization code and state from request
    code = request.GET.get("code")
    state = request.GET.get("state")

    # Initialize Google OAuth handler
    google_oauth = GoogleOAuth(request)

    # Validate state to prevent CSRF
    if not google_oauth.validate_state(state):
        # Invalid state, return error
        return Response({"error": "Invalid state"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Exchange authorization code for tokens
        token_response = google_oauth.exchange_code_for_token(code)

        # Get access token
        access_token = token_response.get("access_token")

        # Get user info
        user_info = google_oauth.get_user_info(access_token)

        # Authenticate or create user
        user, created = google_oauth.authenticate_or_create_user(user_info)

        # Log in user
        token_manager = TokenService(user=user, request=request)
        basic_serializer = get_serializer_class(
            auth_config.basic_account_serializer_class
        )
        response = Response(
            data={
                "status": "success",
                "user": basic_serializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        response_data = token_manager.setup_login_cookies(response=response)
        response = response_data["response"]
        tokens = response_data["tokens"]
        response.data["access_token"] = tokens["access_token"]
        response.data["refresh_token"] = tokens["refresh_token"]

        # Store refresh token in user's session or database
        refresh_token = token_response.get("refresh_token")
        if refresh_token:
            # You might want to securely store this
            request.session["google_refresh_token"] = refresh_token

        # Redirect to dashboard or home page
        return HttpResponseRedirect(reverse("dashboard"))

    except Exception as e:
        logger.error(e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
