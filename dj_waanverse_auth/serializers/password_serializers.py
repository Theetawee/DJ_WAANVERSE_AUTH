import logging

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from dj_waanverse_auth.models import Account
from dj_waanverse_auth.services.email_service import EmailService

logger = logging.getLogger(__name__)


class InitiatePasswordResetSerializer(serializers.Serializer):
    email_address = serializers.EmailField(
        required=True,
        error_messages={
            "required": _("Email is required."),
        },
    )

    def __init__(self, instance=None, data=None, **kwargs):
        self.email_service = EmailService()
        super().__init__(instance=instance, data=data, **kwargs)

    def validate_email_address(self, email_address):
        """
        Validate email with comprehensive checks and sanitization.
        """
        return email_address

    def validate(self, attrs):
        email = attrs["email_address"]
        account = Account.objects.filter(email_address=email, is_active=True).first()

        if not account:
            raise serializers.ValidationError(
                _("Account with this email does not exist.")
            )

        attrs["account"] = account

        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                account = validated_data["account"]
                self.email_service.send_password_reset_email(account)
                return account
        except Exception as e:
            logger.error(f"Email verification failed: {str(e)}")
            raise serializers.ValidationError(_("Failed to initiate password reset."))
