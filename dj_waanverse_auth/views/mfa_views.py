from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def activate_mfa_view(request):
    return Response({"status": "success"}, status=status.HTTP_200_OK)
