from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from logging import getLogger
from rest_framework.permissions import AllowAny
from rest_framework.decorators import permission_classes
from dj_waanverse_auth.utils.email_utils import request_code_flow
from dj_waanverse_auth.utils.login import verify_code_flow

logger = getLogger(__name__)
Account = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    email_address = request.data.get("email_address")
    code = request.data.get("code")
    platform = request.query_params.get("platform", "web")  # web or app

    if email_address is None:
        return Response(
            {"detail": "Email address is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if code is None:
        return request_code_flow(email_address, platform, is_signup=False)

    return verify_code_flow(request, email_address, code)
