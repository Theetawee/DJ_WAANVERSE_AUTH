from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


@swagger_auto_schema(
    method="get",
    operation_summary="Welcome message",
    operation_description="Welcome message for the DJ_WAANVERSE_AUTH API",
    responses={
        200: openapi.Response(
            "Success",
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "msg": openapi.Schema(
                        type=openapi.TYPE_STRING, description="Welcome message"
                    ),
                },
            ),
        )
    },
)
@api_view(["GET"])
def index(request):
    """
    A simple view that returns a welcome message.
    """
    return Response(
        data={"msg": "Welcome to DJ_WAANVERSE_AUTH"}, status=status.HTTP_200_OK
    )
