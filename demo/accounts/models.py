"""
Custom user model"""

from django.db import models

from dj_waanverse_auth.base_account import AbstractBaseAccount


class Account(AbstractBaseAccount):
    name = models.CharField(max_length=255, verbose_name="Name", blank=True, null=True)
    date_of_birth = models.DateField(
        verbose_name="Date of Birth", blank=True, null=True
    )

    def get_full_name(self):
        return self.name or self.email_address
