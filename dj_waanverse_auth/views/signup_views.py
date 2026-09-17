from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from dj_waanverse_auth import settings as auth_config
from django.utils.module_loading import import_string


class SignupView(APIView):
    permission_classes = [AllowAny]

    # throttle_classes = [SignupIdentifierThrottle, SignupIPThrottle]
    def get_serializer_class(self):
        serializer_path = auth_config.signup_serializer_class
        return import_string(serializer_path)

    def post(self, request):
        if auth_config.disable_signup:
            return Response(
                {"msg": "Something went wrong. Please try again later."},
                status=status.HTTP_403_FORBIDDEN,
            )
        SerializerClass = self.get_serializer_class()
        serializer = SerializerClass(data=request.data, context={"request": request})

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"msg": "Account created successfully."},
                status=status.HTTP_201_CREATED,
            )

        error_msg = "Invalid request payload."
        if serializer.errors:
            first_field = list(serializer.errors.keys())[0]
            errors = serializer.errors[first_field]
            error_msg = errors[0] if isinstance(errors, list) else str(errors)

        return Response({"msg": error_msg}, status=status.HTTP_400_BAD_REQUEST)
