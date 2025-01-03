from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from dj_waanverse_auth.serializers import SignupSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def signup_view(request):
    """
    Function-based view to handle user signup.
    """
    serializer = SignupSerializer(data=request.data)
    if serializer.is_valid():
        try:
            user = serializer.create(serializer.validated_data)
            return Response(
                {
                    "message": "Account created successfully.",
                    "user": {
                        "email": user.email,
                        "username": user.username,
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to create account: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
