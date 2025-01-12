from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class AccountManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")

        email = extra_fields.get("email_address")
        phone = extra_fields.get("phone_number")
        if not email and not phone:
            raise ValueError("Either email address or phone number must be provided")

        user = self.model(username=username, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password, **extra_fields):
        return self.create_user(
            username=username,
            password=password,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            **extra_fields
        )


class AbstractBaseAccount(AbstractBaseUser, PermissionsMixin):
    """
    Abstract base user model with support for both email and phone authentication.
    Includes core user management functionality and flexible contact methods.
    """

    username = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        help_text="Required. 10 characters or fewer.",
    )
    email_address = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Email",
        db_index=True,
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
    password_last_updated = models.DateTimeField(default=timezone.now)
    email_verified = models.BooleanField(default=False)
    phone_number_verified = models.BooleanField(default=False)

    objects = AccountManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        abstract = True
        constraints = [
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

    def clean(self):
        if not self.email_address and not self.phone_number:
            raise ValidationError(
                "At least one contact method (email or phone number) must be provided."
            )
        super().clean()

    def __str__(self):
        return self.get_primary_contact() or self.username

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

    @property
    def get_primary_contact(self):
        return self.email_address or self.phone_number

    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return True
