import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from dj_waanverse_auth.serializers.login_serializers import LoginSerializer
from dj_waanverse_auth.services import email_service, token_service
from dj_waanverse_auth.services.utils import get_serializer_class
from dj_waanverse_auth.settings import auth_config

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """View for user login."""
    try:
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            token_manager = token_service.TokenService(user=user)
            tokens = token_manager.generate_tokens()
            basic_serializer = get_serializer_class(
                auth_config.basic_account_serializer_class
            )
            email_manager = email_service.EmailService(request=request)
            email_manager.send_login_alert(user.email_address)
            response = Response(
                data={
                    "status": "success",
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "user": basic_serializer(user).data,
                }
            )
            return token_manager.add_tokens_to_response(response, tokens)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.exception(f"Error occurred while logging in. Error: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
