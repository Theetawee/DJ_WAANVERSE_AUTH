from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from dj_waanverse_auth.throttles import SignupIdentifierThrottle, SignupIPThrottle
from dj_waanverse_auth import settings as auth_config
from django.utils.module_loading import import_string
from rest_framework.exceptions import PermissionDenied


class SignupView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [SignupIdentifierThrottle, SignupIPThrottle]

    # throttle_classes = [SignupIdentifierThrottle, SignupIPThrottle]
    def get_serializer_class(self):
        serializer_path = auth_config.signup_serializer_class
        return import_string(serializer_path)

    def post(self, request):
        if auth_config.disable_signup:
            raise PermissionDenied("Something went wrong. Please try again later.")
        SerializerClass = self.get_serializer_class()
        serializer = SerializerClass(data=request.data, context={"request": request})

        serializer.is_valid(raise_exception=True)
        resp = serializer.save()
        registration_type = resp["registration_type"]
        return Response(
            {
                "msg": "Account created successfully.",
                "registration_type": registration_type,
            },
            status=status.HTTP_201_CREATED,
        )
