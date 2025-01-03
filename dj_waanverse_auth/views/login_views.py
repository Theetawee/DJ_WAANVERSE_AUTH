from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from dj_waanverse_auth.serializers.login_serializers import LoginSerializer
from dj_waanverse_auth.services.token_service import TokenService


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """View for user login."""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data["user"]
        token_service = TokenService(user=user)
        tokens = token_service.generate_tokens()
        response = Response(
            data={
                "status": "success",
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "user": str(user),
            }
        )
        return token_service.add_tokens_to_response(response, tokens)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
