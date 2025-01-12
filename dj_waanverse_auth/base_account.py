from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class AccountManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username field must be set")

        email = extra_fields.get("email_address")
        phone = extra_fields.get("phone_number")
        if not email and not phone:
            raise ValueError("Either email address or phone number must be provided")

        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username=username, password=password, **extra_fields)


class AbstractBaseAccount(AbstractBaseUser, PermissionsMixin):
    """
    Abstract base user model that can be extended.
    Provides core authentication fields and functionality.
    """

    username = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        help_text="Required. 10 characters or fewer.",
    )
    email_address = models.EmailField(
        max_length=255, blank=True, null=True, verbose_name="Email", db_index=True
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="E.164 format recommended (+1234567890)",
        db_index=True,
    )
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    password_last_updated = models.DateTimeField(auto_now=True)
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
                name="unique_phone_number",
                condition=~Q(phone_number=None),
            ),
            models.UniqueConstraint(
                fields=["email_address"],
                name="unique_email_address",
                condition=~Q(email_address=None),
            ),
        ]

    def clean(self):
        """Validate that either email or phone is provided"""
        if not self.email_address and not self.phone_number:
            raise ValidationError(
                "At least one contact method (email or phone number) must be provided."
            )
        super().clean()

    def __str__(self):
        return self.email_address or self.phone_number or self.username

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return True

    def get_primary_contact(self):
        """Returns the primary contact method (email or phone)"""
        return self.email_address or self.phone_number
