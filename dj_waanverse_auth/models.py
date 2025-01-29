import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dj_waanverse_auth.config.settings import auth_config

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


class UserSession(models.Model):
    """
    Represents a user's session tied to a specific device and account.
    Used for tracking and managing session-related data.
    """

    session_id = models.CharField(max_length=64, unique=True)
    account = models.ForeignKey(
        Account, related_name="sessions", on_delete=models.CASCADE
    )
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    login_method = models.CharField(max_length=255, blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(default=timezone.now)

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["account", "is_active"]),
            models.Index(fields=["session_id"]),
        ]
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"

    def __str__(self):
        return f"Session: {self.session_id}, Account: {self.account}"

    def mark_active(self):
        """
        Marks the session as active and updates the last_used timestamp.
        """
        self.last_used = timezone.now()
        self.save(update_fields=["last_used", "last_updated"])


class ResetPasswordToken(models.Model):
    account = models.ForeignKey(
        Account, related_name="reset_password_tokens", on_delete=models.CASCADE
    )
    code = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    @classmethod
    def generate_code(cls):
        """Generate a secure random code."""
        return secrets.token_urlsafe(auth_config.password_reset_code_length)

    @classmethod
    def create_for_user(cls, user):
        """Create a new reset token for user, invalidating any existing ones."""
        cls.objects.filter(account=user, is_used=False).update(is_used=True)
        return cls.objects.create(account=user, code=cls.generate_code())

    def is_expired(self):
        """Check if the reset password token is expired."""
        expiration_time = self.created_at + timedelta(
            minutes=auth_config.password_reset_expiry_in_minutes
        )
        return timezone.now() > expiration_time or self.is_used

    def use_token(self):
        """Mark token as used."""
        self.is_used = True
        self.save()

    def __str__(self):
        return f"Reset token for {self.account.email_address}"
