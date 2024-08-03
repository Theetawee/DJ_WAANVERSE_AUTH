"""
Custom user model     """

from django.utils import timezone
from datetime import timedelta


from django.db import models


class EmailConfirmationCode(models.Model):
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_expired(self):
        expiration_time = self.created_at + timedelta(minutes=10)
        return timezone.now() > expiration_time

    def __str__(self):
        return f"Email: {self.email} - Code: {self.code}"


class UserLoginActivity(models.Model):
    # Login Status
    SUCCESS = "S"
    FAILED = "F"

    LOGIN_STATUS = ((SUCCESS, "Success"), (FAILED, "Failed"))

    login_IP = models.GenericIPAddressField(null=True, blank=True)
    login_datetime = models.DateTimeField(auto_now=True)
    login_username = models.CharField(max_length=40, null=True, blank=True)
    status = models.CharField(
        max_length=1, default=SUCCESS, choices=LOGIN_STATUS, null=True, blank=True
    )
    user_agent_info = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.login_username} - {self.login_datetime}"


class ResetPasswordCode(models.Model):
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    code = models.CharField(max_length=6, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.IntegerField(default=1)

    @property
    def is_expired(self):
        expiration_time = self.created_at + timedelta(minutes=10)
        return timezone.now() > expiration_time

    def __str__(self):
        return f"Email: {self.email} - Code: {self.code}"
