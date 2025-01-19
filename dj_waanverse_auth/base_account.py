"""
    Abstract base user model that supports both email and phone authentication.

    Includes core user management functionality and flexible contact methods."""

from typing import Optional

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.db.models import Q
from django.utils import timezone


class AccountManager(BaseUserManager):
    """
    Custom manager for creating users and superusers with both username and email/phone support.
    """

    def create_user(
        self,
        username: str,
        email_address: str,
        password: Optional[str] = None,
        **extra_fields
    ) -> AbstractBaseUser:
        """
        Create and return a regular user with a username and email address.
        """
        if not username:
            raise ValueError("Username is required")

        if not email_address:
            raise ValueError("Either email address must be provided")

        user = self.model(
            username=username, email_address=email_address, **extra_fields
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(
        self, username: str, email_address: str, password: str, **extra_fields
    ) -> AbstractBaseUser:
        """
        Create and return a superuser with the given username, email, and password.
        """
        return self.create_user(
            username=username,
            password=password,
            email_address=email_address,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            **extra_fields
        )


class AbstractBaseAccount(AbstractBaseUser, PermissionsMixin):
    """
    Abstract base user model that supports both email and phone authentication.
    Includes core user management functionality and flexible contact methods.
    """

    username: str = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        help_text="Required. 10 characters or fewer.",
    )
    email_address: str = models.EmailField(
        max_length=255,
        verbose_name="Email",
        db_index=True,
    )
    phone_number: Optional[str] = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="E.164 format recommended (+1234567890)",
        db_index=True,
    )
    date_joined: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    last_login: Optional[models.DateTimeField] = models.DateTimeField(
        null=True, blank=True
    )
    is_active: bool = models.BooleanField(default=True)
    is_staff: bool = models.BooleanField(default=False)
    password_last_updated: models.DateTimeField = models.DateTimeField(
        default=timezone.now
    )
    email_verified: bool = models.BooleanField(default=False)
    phone_number_verified: bool = models.BooleanField(default=False)

    objects = AccountManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email_address"]

    class Meta:
        """
        Meta class for the AbstractBaseAccount model.
        """

        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["phone_number"],
                name="%(app_label)s_%(class)s_unique_phone",
                condition=~Q(phone_number=None),
            )
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
        """
        Return a string representation of the user.
        Defaults to the primary contact (email or phone) or the username.
        """
        return self.get_primary_contact or self.username

    def get_full_name(self) -> str:
        """
        Return the full name of the user, which is the username in this case.
        """
        return self.username

    def get_short_name(self) -> str:
        """
        Return the short name of the user, which is the username in this case.
        """
        return self.username

    @property
    def get_primary_contact(self) -> Optional[str]:
        """
        Return the primary contact method for the user, which is either email or phone number.
        """
        return self.email_address or self.phone_number

    def has_perm(self, perm: str, obj: Optional[object] = None) -> bool:
        """
        Check if the user has the specified permission. Only staff members have permissions.
        """
        return self.is_staff

    def has_module_perms(self, app_label: str) -> bool:
        """
        Check if the user has permission to access the given app label.
        """
        return True
