from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """View for user login."""
    print("called")
    # Your login logic here
    return Response({"message": "Login successful!"}, status=status.HTTP_200_OK)
