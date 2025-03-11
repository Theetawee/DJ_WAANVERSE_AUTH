import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from dj_waanverse_auth import settings
from dj_waanverse_auth.models import ResetPasswordToken
from dj_waanverse_auth.services.email_service import EmailService

logger = logging.getLogger(__name__)
Account = get_user_model()


class InitiatePasswordResetSerializer(serializers.Serializer):
    email_address = serializers.EmailField(
        required=True,
        error_messages={
            "required": _("Email is required."),
            "invalid": _("Please enter a valid email address."),
        },
    )

    def __init__(self, instance=None, data=None, **kwargs):
        self.email_service = EmailService()
        super().__init__(instance=instance, data=data, **kwargs)

    def validate_email_address(self, email_address):
        """Validate and normalize email address."""
        return email_address.lower().strip()

    def validate(self, attrs):
        email = attrs["email_address"]
        account = Account.objects.filter(email_address=email, is_active=True).first()
        if not account:
            raise serializers.ValidationError(
                {"email_address": _("No active account found with this email address.")}
            )

        attrs["account"] = account
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                account = validated_data["account"]
                token = ResetPasswordToken.create_for_user(account)
                self.email_service.send_email(
                    subject=settings.password_reset_email_subject,
                    template_name="emails/password_reset.html",
                    recipient=account.email_address,
                    context={"token": token.code},
                )
                return account
        except Exception as e:
            logger.error(f"Password reset initiation failed: {str(e)}", exc_info=True)
            raise serializers.ValidationError(
                _("Unable to process password reset request.")
            )


class ResetPasswordSerializer(serializers.Serializer):
    email_address = serializers.EmailField(required=True)
    code = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": _("Passwords do not match.")}
            )

        try:
            validate_password(attrs["new_password"])
        except Exception as e:
            raise serializers.ValidationError({"new_password": list(e)})

        try:
            user = Account.objects.get(email_address=attrs["email_address"])
        except Account.DoesNotExist:
            raise serializers.ValidationError(
                {"email_address": _("No account found with this email address.")}
            )

        try:
            token = ResetPasswordToken.objects.get(
                account=user, code=attrs["code"], is_used=False
            )
            if token.is_expired():
                raise serializers.ValidationError(
                    {"code": _("Reset code has expired.")}
                )
        except ResetPasswordToken.DoesNotExist:
            raise serializers.ValidationError({"code": _("Invalid reset code.")})

        attrs["user"] = user
        attrs["token"] = token
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        token = self.validated_data["token"]

        with transaction.atomic():
            user.set_password(self.validated_data["new_password"])
            user.password_last_updated = timezone.now()
            user.save()

            token.use_token()
