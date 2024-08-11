import pyotp
from django.contrib.auth import get_user_model, logout, user_logged_in
from django.contrib.auth.models import update_last_login
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import MultiFactorAuth
from .serializers import (
    DeactivateMfaSerializer,
    LoginSerializer,
    LogoutSerializer,
    MfaCodeSerializer,
    ResetPasswordSerializer,
    ReVerifyEmailSerializer,
    VerifyEmailSerializer,
    VerifyResetPasswordSerializer,
)
from .settings import accounts_config
from .utils import (
    EmailThread,
    get_client_ip,
    get_serializer,
    reset_response,
    set_cookies,
)

Account = get_user_model()


@api_view(["POST"])
@throttle_classes([UserRateThrottle])
@permission_classes([AllowAny])
def login_view(request):
    USER_CLAIM_SERIALIZER = get_serializer(accounts_config.USER_CLAIM_SERIALIZER_CLASS)
    serializer = LoginSerializer(data=request.data, context={"request": request})

    if serializer.is_valid():
        mfa = serializer.validated_data.get("mfa", False)
        refresh_token = serializer.validated_data.get("refresh_token", "")
        access_token = serializer.validated_data.get("access_token", "")
        user = serializer.validated_data.get("user", None)
        email_verified = serializer.validated_data.get("email_verified", False)

        # Handle response based on email verification and MFA
        if not email_verified:
            response_data = {"email": user.email, "status": "unverified"}
            response_status = status.HTTP_200_OK
        elif mfa:
            response_data = {"mfa": user.id}
            response_status = status.HTTP_200_OK
            response = Response(response_data, status=response_status)
            response = set_cookies(mfa=user.id, response=response)
            response = reset_response(response)
            return response
        else:
            response_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": USER_CLAIM_SERIALIZER(user).data,
            }
            response_status = status.HTTP_200_OK

        response = Response(response_data, status=response_status)
        response = set_cookies(
            response=response, access_token=access_token, refresh_token=refresh_token
        )
        return response

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token_view(request):
    refresh_token = request.data.get("refresh") or request.COOKIES.get(
        accounts_config["REFRESH_TOKEN_COOKIE_NAME"]
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


class ResendEmail(APIView):
    throttle_scope = "email"

    def post(self, request):
        """
        Collect email from the user to resend the verification email.
        """
        serializer = ReVerifyEmailSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.save()
            return Response(
                {"email": email, "status": "email-sent"},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


resend_verification_email = ResendEmail.as_view()


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_email(request):
    """
    Verify email
    """
    serializer = VerifyEmailSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data["email"]
        return Response(
            {"email": email, "status": "verified"}, status=status.HTTP_200_OK
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def signup_view(request):
    SignupSerializer = get_serializer(accounts_config["SIGNUP_SERIALIZER"])
    serializer = SignupSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()

        response = Response(
            {
                "email": user.email,
                "status": "unverified",
            },
            status=status.HTTP_201_CREATED,
        )

        return response

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enable_mfa(request):
    user = request.user
    try:
        account_mfa, created = MultiFactorAuth.objects.get_or_create(account=user)

        if not account_mfa.secret_key:
            # Ensure the generated key is unique
            unique_key_generated = False
            while not unique_key_generated:
                potential_key = pyotp.random_base32()
                if not MultiFactorAuth.objects.filter(
                    secret_key=potential_key
                ).exists():
                    account_mfa.secret_key = potential_key
                    unique_key_generated = True

        # Generate the OTP provisioning URI
        otp_url = pyotp.TOTP(account_mfa.secret_key, digits=6).provisioning_uri(
            user.username, issuer_name=accounts_config["MFA_ISSUER"]
        )

        account_mfa.save()

        return Response(
            {"url": otp_url, "key": account_mfa.secret_key}, status=status.HTTP_200_OK
        )
    except MultiFactorAuth.DoesNotExist:
        return Response(
            {"error": "MFA configuration could not be created."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        return Response(
            {"error": f"An error occurred: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_mfa(request):
    user = request.user
    try:
        mfa_account = MultiFactorAuth.objects.get(account=user)
    except Exception as e:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": str(e)})
    if mfa_account.activated:
        return Response({"msg": "MFA already activated"}, status=status.HTTP_200_OK)

    serializer = MfaCodeSerializer(data=request.data)

    if serializer.is_valid():
        code = serializer.validated_data.get("code")
        totp = pyotp.TOTP(mfa_account.secret_key)

        if totp.verify(code):
            mfa_account.activated = True
            mfa_account.set_recovery_codes()
            mfa_account.save()
            return Response(
                {"msg": "2FA enabled successfully"}, status=status.HTTP_200_OK
            )
        else:
            return Response({"msg": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mfa_status(request):
    user = request.user
    try:
        mfa_account = MultiFactorAuth.objects.get(account=user)
        return Response(
            data={
                "mfa_status": mfa_account.activated,
                "recovery_codes": mfa_account.recovery_codes,
            },
            status=status.HTTP_200_OK,
        )
    except MultiFactorAuth.DoesNotExist:
        return Response(
            data={"mfa_status": False, "recovery_codes": []},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            data={"error": f"An error occurred: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def regenerate_recovery_codes(request):
    user = request.user
    try:
        # Retrieve the MultiFactorAuth instance
        mfa_account = MultiFactorAuth.objects.get(account=user)

        if not mfa_account.activated:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"error": "MFA is not activated. Please activate MFA first."},
            )

        # Generate new recovery codes
        mfa_account.set_recovery_codes()
        mfa_account.save()
        if accounts_config["MFA_EMAIL_ALERTS"]:
            thread = EmailThread(
                email=user.email,
                template="regenerate_codes",
                subject="New MFA Recovery Codes Generated",
                context={
                    "username": user.username,
                    "email": user.email,
                    "time": timezone.now(),
                    "ip_address": get_client_ip(request),
                    "user_agent": request.META.get("HTTP_USER_AGENT", "<unknown>")[
                        :255
                    ],
                },
            )
            thread.start()
        return Response(
            status=status.HTTP_200_OK,
            data={"msg": "Recovery codes generated successfully"},
        )
    except MultiFactorAuth.DoesNotExist:
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={"error": "MFA configuration not found. Please activate MFA first."},
        )
    except Exception as e:
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={
                "error": f"An error occurred while generating recovery codes: {str(e)}"
            },
        )


class DeactivateMfaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = DeactivateMfaSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "MFA has been deactivated."}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_info(request):
    AccountSerializer = get_serializer(accounts_config["USER_DETAIL_SERIALIZER"])
    user = request.user
    serializer = AccountSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
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
    user_id = request.COOKIES.get(accounts_config["MFA_COOKIE_NAME"])
    User_Claim_Serializer = get_serializer(accounts_config["USER_CLAIM_SERIALIZER"])
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
        mfa_account = MultiFactorAuth.objects.get(account=user)
    except Account.DoesNotExist:
        return Response({"msg": "Invalid account"}, status=status.HTTP_400_BAD_REQUEST)

    if not mfa_account.activated:
        return Response(
            {"msg": "MFA is not activated for this user"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    code = request.data.get("code", 0)
    totp = pyotp.TOTP(mfa_account.secret_key)

    if totp.verify(code):
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

    elif code in mfa_account.recovery_codes:
        # Recovery code is valid
        mfa_account.recovery_codes.remove(code)  # Remove used recovery code
        mfa_account.save()
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
    else:
        return Response(
            {"msg": "Invalid OTP or recovery code"}, status=status.HTTP_400_BAD_REQUEST
        )

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
            "user": User_Claim_Serializer(user).data,
        },
        status=status.HTTP_200_OK,
    )

    response = set_cookies(
        response=response, access_token=access, refresh_token=refresh
    )
    response.delete_cookie(accounts_config["MFA_COOKIE_NAME"])

    return response


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    if request.user.is_authenticated:
        return Response(
            {"msg": "You are already authenticated."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = ResetPasswordSerializer(data=request.data)
    if serializer.is_valid():
        reset_code = serializer.save()
        return Response(
            {
                "msg": "Password reset code has been sent successfully.",
                "attempts": reset_code.attempts,
                "email": reset_code.email,
            },
            status=status.HTTP_200_OK,
        )
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
