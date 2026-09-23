from __future__ import annotations

from logging import getLogger

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from dj_waanverse_auth.throttles import (
    PasswordResetRequestIdentifierThrottle,
    PasswordResetConfirmIPThrottle,
    PasswordResetRequestIPThrottle,
)
from dj_waanverse_auth.models import PasswordResetCode, Session
from dj_waanverse_auth.notifications.dispatch import send_verification_sms
from dj_waanverse_auth.notifications.email import (
    send_verification_code_email,
    send_verification_link_email,
)
from dj_waanverse_auth.utils import identifiers as identifier_utils
from dj_waanverse_auth.utils.security.cookies import build_auth_response
from dj_waanverse_auth.utils.security.tokens import issue_tokens_for_account

logger = getLogger(__name__)

Account = get_user_model()

MAX_PASSWORD_LENGTH = 128
GENERIC_SENT_MESSAGE = (
    "If an account matching that identifier exists, a password reset "
    "code has been sent."
)
GENERIC_RESET_ERROR = "This code or link is invalid or has expired."


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [
        PasswordResetRequestIdentifierThrottle,
        PasswordResetRequestIPThrottle,
    ]

    def post(self, request):
        identifier = request.data.get("identifier")
        delivery = request.data.get("delivery", "code")

        if not isinstance(identifier, str) or not identifier.strip():
            return Response(
                {"msg": "Identifier is required."}, status=status.HTTP_400_BAD_REQUEST
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
                {"msg": "Invalid identifier."}, status=status.HTTP_400_BAD_REQUEST
            )

        if identifier_type == "phone" and delivery == "link":
            return Response(
                {"msg": "Phone reset only supports codes, not links."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account = self._get_active_account(identifier_type, identifier)

        if account is not None:
            _, code, token = PasswordResetCode.issue_for(account)
            self._deliver(
                account=account,
                identifier_type=identifier_type,
                delivery=delivery,
                code=code,
                token=token,
            )
        else:
            logger.info(
                "Password reset requested for non-existent or inactive identifier."
            )

        return Response({"msg": GENERIC_SENT_MESSAGE}, status=status.HTTP_200_OK)

    def _get_active_account(self, identifier_type, identifier):
        # Note: is_active=True here — the inverse of verification's
        # is_active=False. An unverified account has no password to
        # "reset" in any meaningful sense yet.
        if identifier_type == "email":
            return Account.objects.filter(
                email_address__iexact=identifier.lower(), is_active=True
            ).first()

        try:
            phone_number, _ = identifier_utils.normalize_phone(identifier)
        except ValueError:
            return None
        return Account.objects.filter(phone_number=phone_number, is_active=True).first()

    def _deliver(self, *, account, identifier_type, delivery, code, token) -> bool:
        try:
            if identifier_type == "email":
                if delivery == "code":
                    send_verification_code_email(account, code)
                else:
                    send_verification_link_email(account, token)
            else:
                send_verification_sms(account.phone_number, code)
            return True
        except Exception:
            logger.exception(
                "Password reset delivery failed for account_id=%s via %s/%s",
                account.pk,
                identifier_type,
                delivery,
            )
            return False


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetConfirmIPThrottle]

    def post(self, request):
        parsed = self._parse_request(request)
        if isinstance(parsed, Response):
            return parsed
        identifier, access, new_password, identifier_type, is_code = parsed

        account = self._get_active_account(identifier_type, identifier)
        if account is None:
            return self._error("Invalid reset request.")

        reset_code = self._get_reset_code(account, access, is_code)
        if reset_code is None:
            return self._error(GENERIC_RESET_ERROR)

        try:
            validate_password(new_password, user=account)
        except ValidationError as exc:
            return Response(
                {"msg": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST
            )

        self._complete_reset(account, reset_code, new_password)
        try:
            tokens = issue_tokens_for_account(account, request=request)
        except Exception:
            logger.exception(
                "Password reset succeeded but token issuance failed for account_id=%s",
                account.pk,
            )
            return Response(
                {"msg": "Password reset successful. Please log in.", "action": "login"},
                status=status.HTTP_200_OK,
            )

        return build_auth_response(
            request,
            tokens,
            data={"msg": "Password reset successful."},
            status_code=status.HTTP_200_OK,
        )

    def _parse_request(self, request):
        identifier = request.data.get("identifier")
        access = request.data.get("access")
        new_password = request.data.get("new_password")

        if not isinstance(identifier, str) or not identifier.strip():
            return self._error("Identifier is required.")
        if not isinstance(access, str) or not access.strip():
            return self._error("Code or link is required.")
        if not isinstance(new_password, str) or not new_password:
            return self._error("New password is required.")
        if len(new_password) > MAX_PASSWORD_LENGTH:
            return self._error("Invalid request payload.")

        identifier = identifier.strip()
        access = access.strip()
        is_code = self._is_code(access)

        identifier_type = identifier_utils.get_identifier_type(identifier)
        if identifier_type is None:
            return self._error("Invalid reset request.")

        if identifier_type == "phone" and not is_code:
            return self._error("Phone reset requires a code, not a link.")
        return identifier, access, new_password, identifier_type, is_code

    @staticmethod
    def _error(message):
        return Response({"msg": message}, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def _get_reset_code(account, access, is_code):
        reset_code = (
            account.password_reset_codes.filter(is_used=False)
            .order_by("-created_at")
            .first()
        )
        if reset_code is None or not reset_code.is_valid_for(is_code=is_code):
            return None
        if not reset_code.matches(access, is_code=is_code):
            reset_code.attempts += 1
            reset_code.save(update_fields=["attempts"])
            return None
        return reset_code

    @staticmethod
    def _complete_reset(account, reset_code, new_password):
        with transaction.atomic():
            reset_code.is_used = True
            reset_code.save(update_fields=["is_used"])

            account.set_password(new_password)
            account.save(update_fields=["password"])

            # Password reset is a security-relevant event — revoke
            # every existing session. If the account was compromised
            # and this reset is the legitimate owner reclaiming it,
            # this is exactly what should happen: the attacker's
            # session dies too. If this reset itself is an attacker
            # (having somehow obtained the code), revoking sessions
            # is still the safer default over leaving old ones alive.
            Session.objects.filter(account=account, is_revoked=False).update(
                is_revoked=True, revoked_at=timezone.now()
            )

    @staticmethod
    def _is_code(access: str) -> bool:
        return access.isdigit() and len(access) == 6

    def _get_active_account(self, identifier_type, identifier):
        if identifier_type == "email":
            return Account.objects.filter(
                email_address__iexact=identifier.lower(), is_active=True
            ).first()
        try:
            phone_number, _ = identifier_utils.normalize_phone(identifier)
        except ValueError:
            return None
        return Account.objects.filter(phone_number=phone_number, is_active=True).first()
