from __future__ import annotations

from logging import getLogger

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from dj_waanverse_auth.notifications.email import (
    send_verification_code_email,
    send_verification_link_email,
)

from dj_waanverse_auth.notifications.dispatch import send_verification_sms
from dj_waanverse_auth.models import VerificationCode
from dj_waanverse_auth.utils import identifiers as identifier_utils

logger = getLogger(__name__)

Account = get_user_model()

GENERIC_SENT_MESSAGE = (
    "If an account matching that identifier exists and needs "
    "verification, a code has been sent."
)


class RequestVerificationView(APIView):
    permission_classes = [AllowAny]

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
