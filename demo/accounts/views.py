from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Account
from dj_waanverse_auth.validators import validate_username


@api_view(["GET"])
@permission_classes([AllowAny])
def check_username_availability(request):
    username = request.query_params.get("username")
    is_valid, message = validate_username(username)
    if not is_valid:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"msg": message})

    if Account.objects.filter(username=username).exists():
        return Response(
            status=status.HTTP_409_CONFLICT, data={"msg": "username already taken"}
        )
    else:
        return Response(status=status.HTTP_200_OK, data={"msg": username})


# @api_view(["PATCH"])
# def update_user_info(request):
#     user = request.user
#     serializer = UserUpdateSerializer(user, data=request.data, partial=True)

#     if serializer.is_valid():
#         serializer.save()
#         data = AccountSerializer(user).data
#         return Response(data, status=status.HTTP_200_OK)

#     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
