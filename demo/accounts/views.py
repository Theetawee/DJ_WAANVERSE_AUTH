from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def index(request):
    return Response(
        data={"msg": "Welcome to DJ_WAANVERSE_AUTH"}, status=status.HTTP_200_OK
    )
