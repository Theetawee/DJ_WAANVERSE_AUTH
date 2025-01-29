from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from dj_waanverse_auth.serializers.client_hints_serializers import ClientInfoSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def home_page(request):
    info = ClientInfoSerializer(request.client_info).data

    data = {
        "client_info": info,
    }

    return Response(data, status=status.HTTP_200_OK)
