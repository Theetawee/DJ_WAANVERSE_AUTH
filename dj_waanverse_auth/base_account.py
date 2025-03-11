from typing import Optional

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.db.models import Q


class AccountManager(BaseUserManager):
    def create_user(
        self,
        username: Optional[str] = None,
        email_address: Optional[str] = None,
        phone_number: Optional[str] = None,
        password: Optional[str] = None,
        **extra_fields
    ):
        from dj_waanverse_auth.validators.validate_username import generate_username

        if not username:
            username = generate_username()
        if not email_address and not phone_number:
            raise ValueError(
                "At least one of username, email address, or phone number is required"
            )

        user = self.model(
            username=username,
            email_address=email_address,
            phone_number=phone_number,
            **extra_fields
        )

        if email_address:
            user.email_address = self.normalize_email(email_address)
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
        phone_number: Optional[str] = None,
        password: str = None,
        **extra_fields
    ):
        if not email_address:
            raise ValueError("Superusers must have an email address")

        return self.create_user(
            username=username,
            email_address=email_address,
            phone_number=phone_number,
            password=password,
            is_staff=True,
            is_superuser=True,
            is_active=True,
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
        blank=True,
        null=True,
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="E.164 format recommended (+1234567890)",
        db_index=True,
    )
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    password_last_updated = models.DateTimeField(null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    phone_number_verified = models.BooleanField(default=False)
    is_account_completed = models.BooleanField(default=False)

    objects = AccountManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                check=Q(email_address__isnull=False) | Q(phone_number__isnull=False),
                name="%(app_label)s_%(class)s_must_have_contact",
            ),
            models.UniqueConstraint(
                fields=["phone_number"],
                name="%(app_label)s_%(class)s_unique_phone",
                condition=~Q(phone_number=None),
            ),
            models.UniqueConstraint(
                fields=["email_address"],
                name="%(app_label)s_%(class)s_unique_email",
                condition=~Q(email_address=None),
            ),
        ]
        indexes = [
            models.Index(
                fields=["username"], name="%(app_label)s_%(class)s_username_idx"
            ),
            models.Index(
                fields=["email_address"], name="%(app_label)s_%(class)s_email_idx"
            ),
            models.Index(
                fields=["phone_number"], name="%(app_label)s_%(class)s_phone_idx"
            ),
        ]

    def __str__(self) -> str:
        return self.get_primary_contact or "Unknown User"

    @property
    def get_primary_contact(self) -> Optional[str]:
        return self.email_address or self.phone_number or self.username

    def get_full_name(self) -> str:
        return self.get_primary_contact or "Unknown"

    def get_short_name(self) -> str:
        return self.get_primary_contact or "Unknown"

    def has_perm(self, perm: str, obj: Optional[object] = None) -> bool:
        return self.is_staff

    def has_module_perms(self, app_label: str) -> bool:
        return True

    @property
    def can_receive_emails(self) -> bool:
        return bool(self.email_address and self.email_verified)
