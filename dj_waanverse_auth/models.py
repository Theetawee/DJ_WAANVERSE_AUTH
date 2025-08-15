from datetime import timedelta
import base64

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import uuid


Account = get_user_model()


class VerificationCode(models.Model):
    email_address = models.EmailField(
        db_index=True,
        verbose_name=_("Email Address"),
    )
    code = models.CharField(
        max_length=255, unique=True, verbose_name=_("Verification Code")
    )
    expires_at = models.DateTimeField(verbose_name=_("Expires At"))

    def is_expired(self):
        """Check if the verification code has expired."""
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Code: {self.code}"

    class Meta:
        verbose_name = _("Verification Code")
        verbose_name_plural = _("Verification Codes")


class UserSession(models.Model):
    """
    Represents a user's session tied to a specific device and account.
    Used for tracking and managing session-related data.
    """

    account = models.ForeignKey(
        Account, related_name="sessions", on_delete=models.CASCADE
    )
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["account", "is_active"]),
        ]
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"

    def __str__(self):
        return f"Session: {self.id}, Account: {self.account}"


class LoginCode(models.Model):
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="login_codes"
    )
    code = models.CharField(max_length=8, db_index=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Login code for {self.account.email_address}"

    class Meta:
        verbose_name = "Login Code"
        verbose_name_plural = "Login Codes"


class WebAuthnCredential(models.Model):
    user = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="webauthn_credentials"
    )
    credential_id = models.BinaryField(max_length=255, unique=True)
    public_key = models.BinaryField()
    sign_count = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Credential for {self.user.username} - {self.name or 'Unnamed'}"

    @property
    def credential_id_b64(self):
        return base64.urlsafe_b64encode(self.credential_id).rstrip(b"=").decode("utf-8")

    @property
    def public_key_b64(self):
        return base64.urlsafe_b64encode(self.public_key).rstrip(b"=").decode("utf-8")


class WebAuthnChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    challenge = models.BinaryField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Challenge {self.id} for {self.user or 'Anonymous'}"

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)

    class Meta:
        verbose_name = "WebAuthn Challenge"
        verbose_name_plural = "WebAuthn Challenges"
