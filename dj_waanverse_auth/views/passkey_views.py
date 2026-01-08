import json
import base64
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)

from dj_waanverse_auth import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from rest_framework import status
from logging import getLogger
from dj_waanverse_auth.models import Passkey
from webauthn import generate_authentication_options
from webauthn import verify_authentication_response
from dj_waanverse_auth.utils.login import handle_login

from django.contrib.auth import get_user_model

Account = get_user_model()


logger = getLogger(__name__)


# Helper to decode bytes from frontend
def base64url_decode(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_begin(request):
    user = request.user

    rp_id = settings.webauthn_domain
    rp_name = settings.webauthn_rp_name

    rp_origin = settings.webauthn_origin

    if not rp_id or not rp_name or not rp_origin:
        logger.error("Webauthn domain or name not configured.")
        return Response(
            {"detail": "Webauthn domain or name not configured."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing_keys = Passkey.objects.filter(user=user)
    exclude_list = [
        PublicKeyCredentialDescriptor(id=pk.credential_id) for pk in existing_keys
    ]

    # 1. Generate options
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_id=str(user.id).encode(),
        user_name=user.username,
        user_display_name=user.username,
        exclude_credentials=exclude_list,
    )

    # 2. Encode the challenge to Base64
    challenge_b64 = base64.b64encode(options.challenge).decode("utf-8")

    # 3. Cryptographically sign the challenge
    # This ensures the frontend cannot tamper with it
    signer = TimestampSigner()
    signed_challenge = signer.sign(challenge_b64)

    # 4. Prepare response
    response_data = json.loads(options_to_json(options))

    # Add the signed challenge to the response data
    # The frontend MUST send this back in the next step
    response_data["challenge_token"] = signed_challenge

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_complete(request):
    try:
        signed_challenge = request.data.get("challenge_token")

        if not signed_challenge:
            return Response(
                {"detail": "Missing challenge_token"}, status=status.HTTP_400_BAD_REQUEST
            )

        signer = TimestampSigner()
        try:
            original_challenge_b64 = signer.unsign(signed_challenge, max_age=120)
        except SignatureExpired:
            return Response(
                {"detail": "Registration timed out. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except BadSignature:
            return Response(
                {"detail": "Invalid challenge signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expected_challenge_bytes = base64.b64decode(original_challenge_b64)

        verification = verify_registration_response(
            credential=request.data,
            expected_challenge=expected_challenge_bytes,
            expected_origin=settings.webauthn_origin,
            expected_rp_id=settings.webauthn_domain,
            require_user_verification=True,
        )

        # -----------------------------------------------------------
        # 4. CHECK IF ALREADY EXISTS (Optional safety)
        # -----------------------------------------------------------
        # If the user tries to register the same device twice
        if Passkey.objects.filter(credential_id=verification.credential_id).exists():
            return Response(
                {"detail": "This passkey is already registered."}, status=400
            )

        key_name = request.data.get("key_name", "My Passkey")

        Passkey.objects.create(
            user=request.user,
            name=key_name,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
        )

        return Response(
            {"status": "created", "message": "Passkey added successfully!"},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.error(f"WebAuthn Error: {e}")
        return Response({"detail": f"Registration failed: {str(e)}"}, status=400)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_begin(request):
    email_address = request.data.get("email_address")

    user_passkeys = []
    if email_address:
        try:
            user = Account.objects.get(email_address=email_address)
            for pk in Passkey.objects.filter(user=user):
                user_passkeys.append(PublicKeyCredentialDescriptor(id=pk.credential_id))
        except Account.DoesNotExist:
            pass

    options = generate_authentication_options(
        rp_id=settings.webauthn_domain,
        allow_credentials=user_passkeys,
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    signer = TimestampSigner()
    challenge_b64 = base64.b64encode(options.challenge).decode("utf-8")
    signed_challenge = signer.sign(challenge_b64)

    response_data = json.loads(options_to_json(options))
    response_data["challenge_token"] = signed_challenge

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_complete(request):
    try:
        # 1. Get Signed Challenge
        signed_challenge = request.data.get("challenge_token")
        if not signed_challenge:
            return Response(
                {"detail": "Missing challenge_token"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Unsign Challenge
        signer = TimestampSigner()
        try:
            original_challenge_b64 = signer.unsign(signed_challenge, max_age=120)
        except (SignatureExpired, BadSignature):
            return Response(
                {"detail": "Login timed out or invalid session"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expected_challenge = base64.b64decode(original_challenge_b64)

        # 3. Find the Passkey in DB
        # The browser sends the Credential ID as 'id' (base64url encoded)
        credential_id = request.data.get("id")

        # We need to find which Passkey object matches this ID
        # Note: Depending on how your DB stores BinaryField, you might need to decode 'id' first
        # But usually, we can iterate or filter.
        # For efficiency, let's decode the incoming ID to bytes to search the DB.
        credential_id_bytes = base64.urlsafe_b64decode(credential_id + "==")

        try:
            passkey = Passkey.objects.get(credential_id=credential_id_bytes)
        except Passkey.DoesNotExist:
            return Response(
                {"detail": "Unknown passkey"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Verify Signature
        verification = verify_authentication_response(
            credential=request.data,
            expected_challenge=expected_challenge,
            expected_origin=settings.webauthn_origin,
            expected_rp_id=settings.webauthn_domain,
            credential_public_key=passkey.public_key,
            credential_current_sign_count=passkey.sign_count,
        )

        # 5. Update Sign Count (Replay attack protection)
        passkey.sign_count = verification.new_sign_count
        passkey.save()

        # 6. LOGIN SUCCESSFUL!
        user = passkey.user

        response = handle_login(request=request, user=user)

        return response

    except Exception as e:
        logger.error(f"Login Error: {e}")
        return Response({"detail": "Login failed"}, status=400)
