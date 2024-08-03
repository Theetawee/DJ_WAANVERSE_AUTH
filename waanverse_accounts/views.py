from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from .serializer import (
    LoginSerializer,
    SignupEmailVerifySerializer,
    VerifyEmailSerializer,
    SignupSerializer,
    AccountSerializer,
    MfaCodeSerializer,
    LogoutSerializer,
    BasicAccountSerializer,
    ResetPasswordSerializer,
    VerifyResetPasswordSerializer,
    UserUpdateSerializer,
)
from django.shortcuts import render
from django.contrib.auth import user_logged_in
from rest_framework.permissions import AllowAny
from .utils import set_cookies
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
import pyotp
from django.contrib.auth import get_user_model
from django.contrib.auth import logout
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth.models import update_last_login
from .utils import is_valid_username
from django.utils.translation import gettext_lazy as _


Account = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    # Any changes to the main login view may affect the mfa login view
    serializer = LoginSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        mfa = serializer.validated_data.get("mfa", False)
        refresh_token = serializer.validated_data.get("refresh", "")
        access_token = serializer.validated_data.get("access", "")
        user = serializer.validated_data.get("user", None)
        if mfa:
            response = Response(status=status.HTTP_200_OK, data={"msg": "mfa"})
            response = set_cookies(mfa=user.id, response=response)
        else:
            response = Response(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": BasicAccountSerializer(user).data,
                },
                status=status.HTTP_200_OK,
            )

            response = set_cookies(
                response, access_token=access_token, refresh_token=refresh_token
            )
        return response
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token_view(request):
    refresh_token = request.data.get("refresh") or request.COOKIES.get(
        settings.BROWSER_CONFIG["REFRESH_COOKIE_NAME"]
    )

    if not refresh_token:
        return Response(
            {"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        refresh = RefreshToken(refresh_token)
        # Generate a new access token
        new_access_token = str(refresh.access_token)
        # Return the new access token in the response
        response = Response({"access": new_access_token}, status=status.HTTP_200_OK)
        new_response = set_cookies(access_token=new_access_token, response=response)
        return new_response
    except TokenError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def collect_email(request):
    """
    Collect email from the user before starting the signin process

    """
    serializer = SignupEmailVerifySerializer(data=request.data)
    if serializer.is_valid():
        instance = serializer.save()
        email = instance.email
        return Response({"email": email}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_email(request):
    """
    Verify email
    """
    serializer = VerifyEmailSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data["email"]

        response = Response({"email": email}, status=status.HTTP_200_OK)

        return response

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def signup_view(request):
    serializer = SignupSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.save()
        refresh_token = data["refresh"]
        access_token = data["access"]
        user = data["user"]

        response = Response(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": user,
            },
            status=status.HTTP_201_CREATED,
        )

        response = set_cookies(
            response, access_token=access_token, refresh_token=refresh_token
        )

        return response

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def enable_mfa(request):
    try:
        user = request.user

        if not user.mfa_secret:
            # Ensure the generated key is unique
            unique_key = False
            while not unique_key:
                potential_key = pyotp.random_base32()
                if not Account.objects.filter(mfa_secret=potential_key).exists():
                    user.mfa_secret = potential_key
                    unique_key = True

        otp_url = pyotp.totp.TOTP(
            user.mfa_secret, digits=6, issuer="Waanverse Accounts"
        ).provisioning_uri(user.username, issuer_name="Waanverse Accounts")
        user.save()

        return Response(
            {"url": otp_url, "key": user.mfa_secret}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(status=status.HTTP_400_BAD_REQUEST, data=str(e))


@api_view(["POST"])
def verify_mfa(request):
    if request.user.mfa_activated:
        return Response({"msg": "MFA already activated"}, status=status.HTTP_200_OK)
    serializer = MfaCodeSerializer(data=request.data)

    if serializer.is_valid():
        user = request.user
        code = serializer.validated_data.get("code")
        totp = pyotp.TOTP(user.mfa_secret)

        if totp.verify(code):
            user.mfa_activated = True
            user.set_recovery_codes()
            user.save()
            return Response(
                {"msg": "2FA enabled successfully"}, status=status.HTTP_200_OK
            )
        else:
            return Response({"msg": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def mfa_activated(request):
    recovery_code = request.user.recovery_codes
    return Response(data={"recovery_codes": recovery_code}, status=status.HTTP_200_OK)


@api_view(["POST"])
def regenerate_recovery_codes(request):
    request.user.set_recovery_codes()
    request.user.save()
    return Response(
        status=status.HTTP_200_OK, data={"msg": "Codes generated successfully"}
    )


@api_view(["POST"])
def deactivate_mfa(request):
    user = request.user
    password = request.data.get("password")

    if not password:
        return Response(
            {"msg": "Please provide us with a valid password to continue."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if user.check_password(password):
        user.mfa_activated = False
        user.mfa_secret = None
        user.save()
        return Response(
            {"msg": "Multi-factor authentication has been deactivated successfully"},
            status=status.HTTP_200_OK,
        )
    else:
        return Response(
            {"msg": "Incorrect password please try again."},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
def user_info(request):
    user = request.user
    serializer = AccountSerializer(user)
    print("called")
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
def logout_view(request):
    serializer = LogoutSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        try:
            serializer.save()
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        logout(request)

        response = Response(
            {"detail": "Successfully logged out."}, status=status.HTTP_200_OK
        )

        # Clear cookies
        for cookie in request.COOKIES:
            response.delete_cookie(cookie)

        return response

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def mfa_login(request):
    user_id = request.COOKIES.get(settings.BROWSER_CONFIG["MFA_COOKIE_NAME"])
    refresh = None
    access = None
    if not user_id:
        return Response(
            {
                "msg": "Unable to verify your account. Please login again.",
                "invalid_account": True,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = Account.objects.get(pk=user_id)
    except Account.DoesNotExist:
        return Response({"msg": "Invalid account"}, status=status.HTTP_400_BAD_REQUEST)

    if not user.mfa_activated:
        return Response(
            {"msg": "MFA is not activated for this user"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    code = request.data.get("code", 0)
    totp = pyotp.TOTP(user.mfa_secret)

    if totp.verify(code):
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

    elif code in user.recovery_codes:
        # Recovery code is valid
        user.recovery_codes.remove(code)  # Remove used recovery code
        user.save()
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
    else:
        return Response(
            {"msg": "Invalid OTP or recovery code"}, status=status.HTTP_400_BAD_REQUEST
        )

    if api_settings.UPDATE_LAST_LOGIN:
        update_last_login(None, user)
    user_logged_in.send(
        sender=user.__class__,
        request=request,
        user=user,
    )

    response = Response(
        {
            "refresh": str(refresh),
            "access": str(access),
            "user": BasicAccountSerializer(user).data,
        },
        status=status.HTTP_200_OK,
    )

    response = set_cookies(
        response=response, access_token=access, refresh_token=refresh
    )
    response.delete_cookie(settings.BROWSER_CONFIG["MFA_COOKIE_NAME"])

    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def check_username_availability(request):
    username = request.query_params.get("username")
    is_valid, message = is_valid_username(username)
    if not is_valid:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"msg": message})

    if Account.objects.filter(username=username).exists():
        return Response(
            status=status.HTTP_409_CONFLICT, data={"msg": "username already taken"}
        )
    else:
        return Response(status=status.HTTP_200_OK, data={"msg": username})


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    serializer = ResetPasswordSerializer(data=request.data)
    if serializer.is_valid():
        reset_code = serializer.save()
        attempts = reset_code.attempts
        email = reset_code.email
        return Response(
            status=status.HTTP_200_OK,
            data={
                "msg": "Password reset successfully",
                "attempts": attempts,
                "email": email,
            },
        )
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_reset_password(request):
    serializer = VerifyResetPasswordSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(
            {"detail": _("Password has been reset successfully.")},
            status=status.HTTP_200_OK,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def email_test(request):
    return render(request, "emails/password_reset.html")


@api_view(["PATCH"])
def update_user_info(request):
    user = request.user
    serializer = UserUpdateSerializer(user, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        data = AccountSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
