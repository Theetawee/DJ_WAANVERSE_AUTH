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
        phone_number: Optional[str] = None,
        phone_region: Optional[str] = None,
        password: Optional[str] = None,
        **extra_fields,
    ):
        if not username and not email_address and not phone_number:
            raise ValueError("A username, email address, or phone number is required.")

        if email_address:
            email_address = self.normalize_email(email_address)

        if phone_number:
            phone_number = phone_number.strip()

        user = self.model(
            username=username,
            email_address=email_address,
            phone_number=phone_number,
            phone_region=phone_region,
            **extra_fields,
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
        phone_number: Optional[str] = None,
        phone_region: Optional[str] = None,
        password: Optional[str] = None,
        **extra_fields,
    ):
        if not username and not email_address and not phone_number:
            raise ValueError("A username, email address, or phone number is required.")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            username=username,
            email_address=email_address,
            phone_number=phone_number,
            phone_region=phone_region,
            password=password,
            **extra_fields,
        )


class AbstractBaseAccount(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        max_length=35,
        unique=True,
        null=True,
        blank=True,
    )

    email_address = models.EmailField(
        max_length=255,
        verbose_name="Email",
        unique=True,
        null=True,
        blank=True,
    )

    phone_number = models.CharField(
        max_length=20,
        verbose_name="Phone Number",
        unique=True,
        null=True,
        blank=True,
    )

    phone_region = models.CharField(
        max_length=10,
        verbose_name="Phone Region",
        blank=True,
        null=True,
    )

    date_joined = models.DateTimeField(
        auto_now_add=True,
    )

    is_active = models.BooleanField(
        default=False,
    )

    is_staff = models.BooleanField(
        default=False,
    )

    email_verified = models.BooleanField(
        default=False,
    )

    phone_verified = models.BooleanField(
        default=False,
    )

    objects = AccountManager()

    USERNAME_FIELD = "username"

    REQUIRED_FIELDS = []

    class Meta:
        abstract = True

    def clean(self):
        super().clean()

        if self.username == "":
            self.username = None
        if self.email_address == "":
            self.email_address = None
        if self.phone_number == "":
            self.phone_number = None

        # At least one identifier must exist.
        if not any(
            [
                self.username,
                self.email_address,
                self.phone_number,
            ]
        ):
            raise ValidationError(
                "A username, email address, or phone number is required."
            )

        # A phone region only makes sense when a phone number exists.
        if self.phone_region and not self.phone_number:
            raise ValidationError(
                "Phone region cannot be provided without a phone number."
            )

        # A verified phone must have a phone number.
        if self.phone_verified and not self.phone_number:
            raise ValidationError(
                "A phone number is required when phone_verified is True."
            )

        # A verified email must have an email address.
        if self.email_verified and not self.email_address:
            raise ValidationError(
                "An email address is required when email_verified is True."
            )

    def __str__(self) -> str:
        return self.email_address or self.phone_number or self.username or str(self.pk)

    def get_full_name(self) -> str:
        return str(self)

    def get_short_name(self) -> str:
        return str(self)
