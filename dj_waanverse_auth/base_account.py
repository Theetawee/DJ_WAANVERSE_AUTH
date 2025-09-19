from typing import Optional
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.exceptions import ValidationError
from django.db import models


class AccountManager(BaseUserManager):
    def create_user(
        self,
        username: Optional[str] = None,
        email_address: Optional[str] = None,
        password: Optional[str] = None,
        **extra_fields
    ):
        from dj_waanverse_auth.utils.generators import generate_username

        if not username:
            username = generate_username()

        if not email_address:
            raise ValueError("Email address is required.")

        user = self.model(
            username=username,
            email_address=self.normalize_email(email_address),
            **extra_fields
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        username: Optional[str] = None,
        email_address: Optional[str] = None,
        password: str = None,
        **extra_fields
    ):
        if not email_address:
            raise ValueError("Superusers must have an email address")

        return self.create_user(
            username=username,
            email_address=email_address,
            password=password,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            email_verified=True,
            **extra_fields
        )


class AbstractBaseAccount(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        max_length=35,
        unique=True,
        db_index=True,
    )
    email_address = models.EmailField(
        max_length=255,
        verbose_name="Email",
        db_index=True,
        unique=True,
    )
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)

    objects = AccountManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email_address"]

    class Meta:
        abstract = True
        indexes = [
            models.Index(
                fields=["username"], name="%(app_label)s_%(class)s_username_idx"
            ),
            models.Index(
                fields=["email_address"], name="%(app_label)s_%(class)s_email_idx"
            ),
        ]

    def clean(self):
        super().clean()
        if not self.email_address:
            raise ValidationError("You must provide an email address.")

    def __str__(self) -> str:
        return self.email_address or self.username

    def get_full_name(self) -> str:
        return self.email_address or self.username

    def get_short_name(self) -> str:
        return self.email_address or self.username

    def has_perm(self, perm: str, obj: Optional[object] = None) -> bool:
        return self.is_staff

    def has_module_perms(self, app_label: str) -> bool:
        return True
