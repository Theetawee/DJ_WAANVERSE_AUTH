from __future__ import annotations

from logging import getLogger
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from dj_waanverse_auth.notifications.email import (
    send_verification_code_email,
    send_verification_link_email,
)
from dj_waanverse_auth import settings as auth_config
from dj_waanverse_auth.notifications.dispatch import send_verification_sms
from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth.utils import identifiers as identifier_utils
from dj_waanverse_auth.utils.security.tokens import issue_tokens_for_account
from dj_waanverse_auth.utils.security.cookies import build_auth_response
from dj_waanverse_auth.throttles import (
    VerificationRequestIdentifierThrottle,
    VerificationRequestIPThrottle,
    VerifyAccountIPThrottle,
)

logger = getLogger(__name__)

Account = get_user_model()
GENERIC_VERIFY_ERROR = "This code or link is invalid or has expired."

GENERIC_SENT_MESSAGE = (
    "If an account matching that identifier exists and needs "
    "verification, a code has been sent."
)


class RequestVerificationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [
        VerificationRequestIdentifierThrottle,
        VerificationRequestIPThrottle,
    ]

    def post(self, request):
        identifier = request.data.get("identifier")
        delivery = request.data.get("delivery", "code")

        if not isinstance(identifier, str) or not identifier.strip():
            return Response(
                {"msg": "Identifier is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if delivery not in ("code", "link"):
            return Response(
                {"msg": "delivery must be 'code' or 'link'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        identifier = identifier.strip()

        identifier_type = identifier_utils.get_identifier_type(identifier)

        if identifier_type is None:
            return Response(
                {"msg": "Invalid identifier."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if identifier_type == "phone" and delivery == "link":
            return Response(
                {"msg": "Phone verification only supports codes, not links."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account = self._get_pending_account(identifier_type, identifier)

        if account is not None:
            verification, code, token = VerificationCode.issue_for(account)
            self._deliver(
                account=account,
                identifier_type=identifier_type,
                delivery=delivery,
                code=code,
                token=token,
            )
        else:
            logger.info(
                "Verification requested for non-existent or already-active "
                "identifier."
            )

        return Response({"msg": GENERIC_SENT_MESSAGE}, status=status.HTTP_200_OK)

    def _get_pending_account(self, identifier_type: str, identifier: str):
        if identifier_type == "email":
            return Account.objects.filter(
                email_address__iexact=identifier.lower(),
                is_active=False,
            ).first()

        try:
            phone_number, _ = identifier_utils.normalize_phone(identifier)
        except ValueError:
            return None

        return Account.objects.filter(
            phone_number=phone_number,
            is_active=False,
        ).first()

    def _deliver(self, *, account, identifier_type, delivery, code, token):
        try:
            if identifier_type == "email":
                if delivery == "code":
                    send_verification_code_email(account, code)
                else:
                    send_verification_link_email(account, token)
            else:
                send_verification_sms(account.phone_number, code)
        except Exception as e:
            logger.critical(
                "Failed to send verification %s to %s: %s",
                delivery,
                identifier_type,
                e,
            )


class VerifyAccountView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [VerifyAccountIPThrottle]

    def post(self, request):
        identifier = request.data.get("identifier")
        access = request.data.get("access")

        validation_error = self._validate_input(identifier, access)
        if validation_error is not None:
            return validation_error

        identifier = identifier.strip()
        access = access.strip()
        is_code = self._is_code(access)

        identifier_type = identifier_utils.get_identifier_type(identifier)
        request_error = self._validate_request(identifier_type, is_code)
        if request_error is not None:
            return request_error

        account = self._get_pending_account(identifier_type, identifier)
        if account is None:
            return self._invalid_request_response()

        verification = self._latest_verification(account)
        if verification is None or not verification.is_valid_for(is_code=is_code):
            return self._invalid_code_response()

        if not verification.matches(access, is_code=is_code):
            self._record_failed_attempt(verification)
            return self._invalid_code_response()

        self._activate_account(account, verification, identifier_type)
        try:
            tokens = issue_tokens_for_account(account, request=request)
        except Exception:
            logger.exception(
                "Verification succeeded but token issuance failed for account_id=%s",
                account.pk,
            )
            return Response(
                {"msg": "Account verified successfully.", "action": "login"},
                status=status.HTTP_200_OK,
            )
        return build_auth_response(
            request,
            tokens,
            data={"msg": "Account verified successfully."},
            status_code=status.HTTP_200_OK,
        )

    @staticmethod
    def _validate_input(identifier, access):
        if not isinstance(identifier, str) or not identifier.strip():
            return Response(
                {"msg": "Identifier is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not isinstance(access, str) or not access.strip():
            return Response(
                {"msg": "Verification code or link is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    @staticmethod
    def _validate_request(identifier_type, is_code):
        if identifier_type is None:
            return VerifyAccountView._invalid_request_response()
        if identifier_type == "phone" and not is_code:
            return Response(
                {"msg": "Phone verification requires a code, not a link."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    @staticmethod
    def _invalid_request_response():
        return Response(
            {"msg": "Invalid verification request."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def _invalid_code_response():
        return Response(
            {"msg": GENERIC_VERIFY_ERROR}, status=status.HTTP_400_BAD_REQUEST
        )

    @staticmethod
    def _latest_verification(account):
        return (
            account.verification_codes.filter(is_used=False)
            .order_by("-created_at")
            .first()
        )

    @staticmethod
    def _record_failed_attempt(verification):
        verification.attempts += 1
        verification.save(update_fields=["attempts"])

    @staticmethod
    def _activate_account(account, verification, identifier_type):
        with transaction.atomic():
            verification.is_used = True
            verification.save(update_fields=["is_used"])

            account.is_active = True
            if identifier_type == "email":
                account.email_verified = True
            else:
                account.phone_verified = True
            account.save(
                update_fields=["is_active", "email_verified", "phone_verified"]
            )

    @staticmethod
    def _is_code(access: str) -> bool:
        return access.isdigit() and len(access) == auth_config.verification_code_length

    def _get_pending_account(self, identifier_type, identifier):
        if identifier_type == "email":
            return Account.objects.filter(
                email_address__iexact=identifier.lower(), is_active=False
            ).first()

        try:
            phone_number, _ = identifier_utils.normalize_phone(identifier)
        except ValueError:
            return None

        return Account.objects.filter(
            phone_number=phone_number, is_active=False
        ).first()
