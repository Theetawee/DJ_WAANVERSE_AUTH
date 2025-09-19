import logging
from django.core.validators import validate_email
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from dj_waanverse_auth.serializers.login_serializers import LoginSerializer
from dj_waanverse_auth.services import token_service
from dj_waanverse_auth.utils.login_utils import handle_login
from dj_waanverse_auth.utils.generators import generate_verification_code
from dj_waanverse_auth.utils.email_utils import send_login_code_email
from dj_waanverse_auth.models import LoginCode, WebAuthnChallenge
from django.core.exceptions import ValidationError
from datetime import timedelta
from dj_waanverse_auth import settings as auth_config
from rest_framework.views import APIView
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    AuthenticatorAttachment,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType,
    AuthenticatorTransport,
)
from dj_waanverse_auth.models import WebAuthnCredential
from webauthn.helpers import options_to_json
import json
import base64

User = get_user_model()

logger = logging.getLogger(__name__)


def decode_base64url(data: str) -> bytes:
    # Add padding if missing
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """View for user login."""
    try:

        email_address = request.data.get("email_address")
        code = request.data.get("code")

        if code:

            serializer = LoginSerializer(
                data=request.data, context={"request": request}
            )
            if serializer.is_valid():
                user = serializer.validated_data["user"]

                response = handle_login(request=request, user=user)
                return response
            else:
                token_manager = token_service.TokenService(request=request)
                response = Response(
                    serializer.errors, status=status.HTTP_400_BAD_REQUEST
                )
                response = token_manager.clear_all_cookies(response)
                return response
        else:
            if not email_address:
                return Response(
                    {"error": "Email address is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                validate_email(email_address)
            except ValidationError:
                return Response(
                    {"error": "Invalid email format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = User.objects.filter(email_address__iexact=email_address).first()

            # Always return success to prevent enumeration
            if not user:
                return Response({"status": "success"}, status=status.HTTP_200_OK)

            # Throttle requests
            recent_code = LoginCode.objects.filter(
                account=user, created_at__gte=timezone.now() - timedelta(seconds=1)
            ).exists()
            if recent_code:
                return Response(
                    {"error": "Please wait before requesting another code."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            LoginCode.objects.filter(account=user).delete()
            code = generate_verification_code()
            LoginCode.objects.create(
                account=user,
                code=code,
                expires_at=timezone.now() + timedelta(minutes=5),
            )

            send_login_code_email(user=user, code=code)

            return Response({"status": "success"}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(f"Error occurred while logging in. Error: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GenerateRegistrationOptionsView(APIView):
    """
    Generates registration options for an authenticated user to add a new passkey.
    Requires the user to be logged in via another method first.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        if (
            auth_config.webauthn_domain is None
            or auth_config.webauthn_rp_name is None
            or auth_config.webauthn_origin is None
        ):
            return Response(
                {"error": "WebAuthn settings are not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        user_id_bytes = str(user.pk).encode("utf-8")

        options = generate_registration_options(
            rp_id=auth_config.webauthn_domain,
            rp_name=auth_config.webauthn_rp_name,
            user_id=user_id_bytes,
            user_name=user.username,
            user_display_name=user.get_full_name(),
            exclude_credentials=[
                PublicKeyCredentialDescriptor(
                    type=PublicKeyCredentialType.PUBLIC_KEY,
                    id=cred.credential_id,
                    transports=[AuthenticatorTransport.INTERNAL],
                )
                for cred in user.webauthn_credentials.all()
            ],
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )

        challenge_record = WebAuthnChallenge.objects.create(
            user=user,
            challenge=options.challenge,
        )

        json_str = options_to_json(options)
        response_data = json.loads(json_str)
        response_data["challengeId"] = str(challenge_record.id)

        return Response(response_data, status=status.HTTP_200_OK)


generate_registration_options_view = GenerateRegistrationOptionsView.as_view()


class VerifyRegistrationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        print(request.data)
        challenge_id = request.data.get("challengeId")

        if not challenge_id:
            return Response(
                {"error": "challengeId is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            challenge_record = WebAuthnChallenge.objects.get(id=challenge_id, user=user)
            expected_challenge = challenge_record.challenge

            challenge_record.delete()

            if challenge_record.is_expired:
                return Response(
                    {"error": "Challenge has expired."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except WebAuthnChallenge.DoesNotExist:
            return Response(
                {"error": "Invalid or expired challenge."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            raw_id_bytes = decode_base64url(request.data["rawId"])

            verified_credential = verify_registration_response(
                credential=request.data,
                expected_challenge=expected_challenge,
                expected_origin=auth_config.webauthn_origin,
                expected_rp_id=auth_config.webauthn_domain,
                require_user_verification=True,
            )

            WebAuthnCredential.objects.create(
                user=user,
                name=request.data.get("name", "Unnamed Passkey"),
                credential_id=raw_id_bytes,
                public_key=verified_credential.credential_public_key,
                sign_count=verified_credential.sign_count,
            )

            return Response({"success": True}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.warning(
                f"WebAuthn registration verification failed for user {user.username}: {e}"
            )
            return Response(
                {"error": f"Could not verify passkey: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            # Handle other unexpected errors
            logger.error(
                f"Unexpected error during WebAuthn registration for user {user.username}: {e}",
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred during verification."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


verify_registration_view = VerifyRegistrationView.as_view()


class GenerateAuthenticationOptionsView(APIView):
    """
    Generates authentication options for a user to log in with a passkey.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        options = generate_authentication_options(
            rp_id=auth_config.webauthn_domain,
            timeout=120000,
            user_verification=UserVerificationRequirement.PREFERRED,
        )
        challenge_record = WebAuthnChallenge.objects.create(
            user=None,
            challenge=options.challenge,
        )
        json_str = options_to_json(options)
        response_data = json.loads(json_str)
        response_data["challengeId"] = str(challenge_record.id)

        return Response(response_data, status=status.HTTP_200_OK)


generate_authentication_options_view = GenerateAuthenticationOptionsView.as_view()


class VerifyAuthenticationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        print(request.data)
        challenge_id = request.data.get("challengeId")
        if not challenge_id:
            return Response(
                {"error": "Challenge not found."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            challenge_record = WebAuthnChallenge.objects.get(id=challenge_id)

            if challenge_record.is_expired:
                return Response(
                    {"error": "Challenge has expired."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            auth_credential_data = request.data
            credential_id_from_client = decode_base64url(
                auth_credential_data.get("rawId")
            )

            db_credential = WebAuthnCredential.objects.filter(
                credential_id=credential_id_from_client
            ).first()

            for credential in WebAuthnCredential.objects.all():
                print(credential.credential_id_b64, " base64")
                print(credential.credential_id, " credential_id")
                print(credential_id_from_client, " credential_id_from_client")
            if not db_credential:
                return Response(
                    {"error": "Credential not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            verified_credential = verify_authentication_response(
                credential=auth_credential_data,
                expected_challenge=challenge_record.challenge,
                expected_origin=auth_config.webauthn_origin,
                expected_rp_id=auth_config.webauthn_domain,
                credential_public_key=db_credential.public_key,
                credential_current_sign_count=db_credential.sign_count,
                require_user_verification=True,
            )

            # Update sign count
            db_credential.sign_count = verified_credential.new_sign_count
            db_credential.save()

            # Delete challenge after successful verification
            challenge_record.delete()

            # Login user
            user = db_credential.user

            response = handle_login(request=request, user=user)

            return response

        except Exception:
            token_manager = token_service.TokenService(request=request)
            response = Response(
                data={"error": "Could not verify passkey"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            response = token_manager.clear_all_cookies(response)
            return response


verify_authentication_view = VerifyAuthenticationView.as_view()
