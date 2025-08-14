import secrets
from datetime import timedelta
import base64

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dj_waanverse_auth.config.settings import auth_config
import uuid


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
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_("Email Address"),
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_("Phone Number"),
    )
    code = models.CharField(
        max_length=255, unique=True, verbose_name=_("Verification Code")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    def is_expired(self):
        """
        Check if the verification code is expired based on the configured expiry duration.
        """
        expiration_time = self.created_at + timedelta(minutes=10)
        return timezone.now() > expiration_time

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


class GoogleStateToken(models.Model):
    state = models.CharField(max_length=255)
    code_verifier = models.CharField(max_length=255)

    def __str__(self):
        return self.state


class LoginCode(models.Model):
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="login_codes"
    )
    code = models.CharField(max_length=8, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    EXPIRATION_MINUTES = 5

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(
            minutes=self.EXPIRATION_MINUTES
        )

    def __str__(self):
        return f"Login code for {self.account.email_address}"

    class Meta:
        verbose_name = "Login Code"
        verbose_name_plural = "Login Codes"
        ordering = ["-created_at"]


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
