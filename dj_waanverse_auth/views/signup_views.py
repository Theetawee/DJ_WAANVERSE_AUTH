import logging

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from dj_waanverse_auth.utils.login_utils import handle_login
from dj_waanverse_auth import settings
from dj_waanverse_auth.serializers.signup_serializers import (
    ActivateEmailSerializer,
    SignupSerializer,
)

logger = logging.getLogger(__name__)

Account = get_user_model()


class SignupView(APIView):
    """
    Class-based view to handle user signup.

    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        if settings.disable_signup:
            return Response(
                {"error": "Something went wrong"},
                status=status.HTTP_403_FORBIDDEN,
            )

        code = request.data.get("code")
        if code:
            serializer = ActivateEmailSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                request.user = user
                response = handle_login(request, user)
                return response

            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = SignupSerializer(
                data=request.data, context={"request": request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"status": "success"},
                    status=status.HTTP_200_OK,
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


signup_view = SignupView.as_view()
