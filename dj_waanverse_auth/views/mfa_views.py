from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dj_waanverse_auth.services.mfa_service import MFAHandler


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_mfa_secret_view(request):
    """Activate MFA for the authenticated user."""
    user = request.user
    mfa_handler = MFAHandler(user)

    if mfa_handler.is_mfa_enabled():

        return Response(
            {"detail": "MFA is already activated."}, status=status.HTTP_400_BAD_REQUEST
        )

    secret_key = mfa_handler.generate_secret()
    provisioning_uri = mfa_handler.get_provisioning_uri()

    return Response(
        {"secret_key": secret_key, "provisioning_uri": provisioning_uri},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def activate_mfa_view(request):
    """Activate MFA for the authenticated user using a code."""
    user = request.user
    mfa_handler = MFAHandler(user)

    if mfa_handler.is_mfa_enabled():
        return Response(
            {"detail": "MFA is already activated."}, status=status.HTTP_400_BAD_REQUEST
        )

    code = request.data.get("code")

    if not code:
        return Response(
            {"detail": "Code is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not mfa_handler.verify_token(code):
        return Response(
            {"detail": "Invalid MFA code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    mfa_handler.activate_mfa()

    return Response({"detail": "MFA has been activated."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def deactivate_mfa_view(request):
    """Deactivate MFA for the authenticated user."""
    user = request.user
    mfa_handler = MFAHandler(user)

    if not mfa_handler.is_mfa_enabled():
        return Response(
            {"detail": "MFA is not activated."}, status=status.HTTP_400_BAD_REQUEST
        )

    password = request.data.get("password")
    code = request.data.get("code")

    if not password or not authenticate(username=user.username, password=password):
        return Response(
            {"detail": "Invalid password."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not code:
        return Response(
            {"detail": "Code is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if mfa_handler.verify_token(code):
        pass
    else:
        return Response(
            {"detail": "Invalid MFA code or recovery code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    mfa_handler.disable_mfa()

    return Response({"detail": "MFA has been deactivated."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_recovery_codes_view(request):
    """Generate new recovery codes for the authenticated user."""
    user = request.user
    mfa_handler = MFAHandler(user)

    if not mfa_handler.is_mfa_enabled():
        return Response(
            {"detail": "MFA is not activated."}, status=status.HTTP_400_BAD_REQUEST
        )

    recovery_codes = mfa_handler.generate_recovery_codes()

    return Response({"recovery_codes": recovery_codes}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_mfa_token_view(request):
    """Verify an MFA token."""
    user = request.user
    token = request.data.get("token")

    if not token:
        return Response(
            {"detail": "MFA token is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    mfa_handler = MFAHandler(user)

    if not mfa_handler.is_mfa_enabled():
        return Response(
            {"detail": "MFA is not activated."}, status=status.HTTP_400_BAD_REQUEST
        )

    is_valid = mfa_handler.verify_token(token)

    if not is_valid:
        return Response(
            {"detail": "Invalid MFA token."}, status=status.HTTP_400_BAD_REQUEST
        )

    return Response(
        {"detail": "MFA token verified successfully."}, status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_recovery_codes_view(request):
    """
    View to get the list of recovery codes for the authenticated user.
    Returns the decrypted recovery codes.
    """
    user = request.user
    mfa_handler = MFAHandler(user)

    if not mfa_handler.is_mfa_enabled():
        return Response(
            {"detail": "MFA is not enabled for this user."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    recovery_codes = mfa_handler.get_recovery_codes()

    if not recovery_codes:
        return Response(
            {"msg": "no_codes"},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response({"recovery_codes": recovery_codes}, status=status.HTTP_200_OK)
