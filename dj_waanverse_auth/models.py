from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


Account = get_user_model()


class AccessCode(models.Model):
    email_address = models.EmailField(
        db_index=True,
        verbose_name=_("Email Address"),
    )
    code = models.CharField(
        max_length=255, unique=True, verbose_name=_("Verification Code")
    )
    expires_at = models.DateTimeField(verbose_name=_("Expires At"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

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
