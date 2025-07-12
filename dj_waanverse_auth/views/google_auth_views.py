from logging import getLogger

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from dj_waanverse_auth import settings
from dj_waanverse_auth.models import GoogleStateToken
from dj_waanverse_auth.utils.login_utils import handle_login
from dj_waanverse_auth.utils.serializer_utils import get_serializer_class

logger = getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def google_login(request):

    GoogleOAuth = get_serializer_class(settings.google_auth_class)
    google_oauth = GoogleOAuth(request)

    # Get authorization URL and store state in session
    auth_url, _, _ = google_oauth.get_authorization_url()

    # Redirect to Google authorization endpoint
    return Response({"url": auth_url}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def google_callback(request):
    code = request.data.get("code")
    state = request.data.get("state")
    GoogleOAuth = get_serializer_class(settings.google_auth_class)
    saved_state = GoogleStateToken.objects.filter(state=state).first()

    if not saved_state:
        return Response({"error": "Invalid state"}, status=status.HTTP_400_BAD_REQUEST)
    # Initialize Google OAuth handler
    google_oauth = GoogleOAuth(request)

    try:
        # Exchange authorization code for tokens
        token_response = google_oauth.exchange_code_for_token(
            code=code, code_verifier=saved_state.code_verifier
        )

        # Get access token
        access_token = token_response.get("access_token")

        # Get user info
        user_info = google_oauth.get_user_info(access_token)

        # Authenticate or create user
        user, created = google_oauth.authenticate_or_create_user(user_info)

        response = handle_login(request=request, user=user)
        saved_state.delete()
        return response

    except Exception as e:
        logger.error(e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
