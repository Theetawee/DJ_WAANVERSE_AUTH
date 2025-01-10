from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dj_waanverse_auth.settings import auth_config

Account = get_user_model()


class MultiFactorAuth(models.Model):
    account = models.OneToOneField(
        Account, related_name="mfa", on_delete=models.CASCADE
    )
    activated = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    recovery_codes = models.JSONField(default=list, blank=True, null=True)
    secret_key = models.CharField(max_length=255, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Account: {self.account} - Activated: {self.activated}"


class VerificationCode(models.Model):
    email_address = models.EmailField(
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_("Email Address"),
    )
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_("Phone Number"),
    )
    is_verified = models.BooleanField(default=False, verbose_name=_("Is Verified"))
    code = models.CharField(
        max_length=255, unique=True, verbose_name=_("Verification Code")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    verified_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Verified At")
    )

    def is_expired(self):
        """
        Check if the verification code is expired based on the configured expiry duration.
        """
        expiration_time = self.created_at + timedelta(
            minutes=auth_config.verification_email_code_expiry_in_minutes
        )
        return timezone.now() > expiration_time

    def __str__(self):
        return f"Code: {self.code}, Verified: {self.is_verified}"

    class Meta:
        verbose_name = _("Verification Code")
        verbose_name_plural = _("Verification Codes")


class UserDevice(models.Model):
    device_id = models.CharField(max_length=255, unique=True)
    account = models.ForeignKey(
        Account, related_name="devices", on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    def __str__(self):
        return f"Device: {self.device_id}, Account: {self.account}"
