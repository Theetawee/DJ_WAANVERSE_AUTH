import secrets

from django.contrib.auth import get_user_model
from django.db import models

from .settings import auth_config

Account = get_user_model()


class MultiFactorAuth(models.Model):
    account = models.OneToOneField(
        Account, related_name="mfa", on_delete=models.CASCADE
    )
    activated = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    recovery_codes = models.JSONField(default=list, blank=True)
    secret_key = models.CharField(max_length=255, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def generate_recovery_codes(self):
        count = int(getattr(auth_config.mfa_recovery_codes))
        return [str(secrets.randbelow(10**7)).zfill(7) for _ in range(count)]

    def set_recovery_codes(self):
        self.recovery_codes = self.generate_recovery_codes()
        self.save()

    def __str__(self):
        return f"Account: {self.account} - Activated: {self.activated}"


# class EmailConfirmationCode(models.Model):
#     user = models.OneToOneField(Account, on_delete=models.CASCADE)
#     code = models.CharField(max_length=6)
#     created_at = models.DateTimeField(auto_now=True)

#     @property
#     def is_expired(self):
#         expiration_time = self.created_at + timedelta(
#             minutes=auth_config.EMAIL_VERIFICATION_CODE_DURATION
#         )
#         return timezone.now() >= expiration_time

#     def __str__(self):
#         return f"Email: {self.user.email} - Code: {self.code}"


# class UserLoginActivity(models.Model):
#     login_IP = models.GenericIPAddressField(null=True, blank=True)
#     login_datetime = models.DateTimeField(auto_now=True)
#     account = models.ForeignKey(Account, on_delete=models.CASCADE)
#     user_agent_info = models.CharField(max_length=255)

#     def __str__(self):
#         return f"{self.account.username} - {self.login_datetime}"


# class ResetPasswordCode(models.Model):
#     email = models.EmailField(max_length=255, unique=True, db_index=True)
#     code = models.CharField(max_length=auth_config.CONFIRMATION_CODE_LENGTH)
#     created_at = models.DateTimeField(auto_now_add=True)

#     @property
#     def is_expired(self):
#         expiration_time = self.created_at + auth_config.PASSWORD_RESET_CODE_DURATION
#         return timezone.now() > expiration_time

#     @property
#     def cooldown_remaining(self):
#         # Calculate cooldown end time
#         cooldown_end_time = self.created_at + timedelta(
#             minutes=auth_config.PASSWORD_RESET_COOLDOWN_PERIOD
#         )
#         return max(cooldown_end_time - timezone.now(), timedelta(seconds=0))

#     def __str__(self):
#         return f"Email: {self.email} - Code: {self.code}"


# class EmailAddress(models.Model):
#     email = models.EmailField(_("email address"), max_length=254)
#     verified = models.BooleanField(default=False)
#     primary = models.BooleanField(default=False)
#     user = models.ForeignKey(
#         Account, on_delete=models.CASCADE, related_name="email_address"
#     )

#     def __str__(self):
#         return self.email
