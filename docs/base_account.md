# Customizing `AbstractBaseAccount`

`AbstractBaseAccount` is an **abstract Django user model** designed to be flexible and extensible. This guide focuses on **customization**—what you need to know when extending it, overriding methods, modifying the manager, or customizing the database schema.

---

## Table of Contents

- [Customizing `AbstractBaseAccount`](#customizing-abstractbaseaccount)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Subclassing the Abstract Model](#subclassing-the-abstract-model)
  - [Customizing the Manager](#customizing-the-manager)
  - [Overriding Methods](#overriding-methods)
  - [Validation](#validation)
  - [Signals](#signals)
  - [Customizing Meta \& Indexes](#customizing-meta--indexes)
  - [Usage Example](#usage-example)
  - [Key Notes](#key-notes)

---

## Overview

`AbstractBaseAccount` provides:

- Unique `username` and `email_address` fields
- Password handling via `AbstractBaseUser`
- Staff and superuser flags
- Email verification flag
- Full and short name methods
- Permission methods (`has_perm`, `has_module_perms`)
- `AccountManager` for creating users and superusers

It is **abstract**, meaning you cannot use it directly in `INSTALLED_APPS`; you must subclass it.

---

## Subclassing the Abstract Model

```python
from django.db import models
from dj_waanverse_auth.base_account import AbstractBaseAccount

class User(AbstractBaseAccount):
    # Add custom fields
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
```

- Always subclass `AbstractBaseAccount` for your project.
- Keep `username` and `email_address` unless you fully replace login logic.
- Add custom fields as needed; they work seamlessly with `AccountManager`.

---

## Customizing the Manager

`AccountManager` provides `create_user` and `create_superuser`. Customize it if you want different behavior for new users.

```python
from dj_waanverse_auth.base_account import AccountManager

class CustomAccountManager(AccountManager):
    def create_user(self, username=None, email_address=None, password=None, **extra_fields):
        # Force usernames to lowercase
        if username:
            username = username.lower()
        return super().create_user(username=username, email_address=email_address, password=password, **extra_fields)
```

**Tips:**

- Call `super().create_user(...)` to keep password hashing and validation intact.
- You can add pre-save logic like default profile creation or formatting emails.

---

## Overriding Methods

You can override methods to customize behavior:

| Method                        | Purpose                                                            |
| ----------------------------- | ------------------------------------------------------------------ |
| `get_full_name()`             | Customize the full name representation (default: `email_address`). |
| `get_short_name()`            | Customize the short name representation.                           |
| `has_perm(perm, obj=None)`    | Define custom permission logic.                                    |
| `has_module_perms(app_label)` | Control access to app modules.                                     |

Example:

```python
def get_full_name(self):
    return f"{self.username} ({self.email_address})"
```

---

## Validation

`AbstractBaseAccount.clean()` validates that `email_address` is provided. You can add extra validation:

```python
def clean(self):
    super().clean()
    if self.username and not self.username.isalnum():
        raise ValidationError("Username must be alphanumeric.")
```

---

## Signals

Hook into user creation or updates using Django signals:

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # e.g., create related profile
        print(f"User {instance.email_address} created")
```

---

## Customizing Meta & Indexes

You can override or extend the `Meta` class in your subclass to:

- Add indexes
- Change ordering
- Add constraints
- Set verbose names

```python
class User(AbstractBaseAccount):
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_premium = models.BooleanField(default=False)

    class Meta(AbstractBaseAccount.Meta):
        verbose_name = "User Account"
        verbose_name_plural = "User Accounts"
        ordering = ["-date_joined", "username"]
        indexes = AbstractBaseAccount.Meta.indexes + [
            models.Index(fields=["is_premium"], name="user_premium_idx"),
            models.Index(fields=["username", "is_active"], name="user_active_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["email_address", "is_premium"], name="unique_email_premium")
        ]
```

**Tips:**

- Inherit `AbstractBaseAccount.Meta` to keep the original indexes intact.
- Add indexes on frequently queried fields for performance.
- Use constraints for unique combinations or checks.

---

## Usage Example

```python
from User.models import User

# Create a regular user
user = User.objects.create_user(
    email_address="user@example.com",
    password="strongpassword123"
)

# Create a superuser
superuser = User.objects.create_superuser(
    email_address="admin@example.com",
    password="supersecurepassword"
)
```

---

## Key Notes

1. **Indexes**: Keep `username` and `email_address` indexes unless you have a specific reason to remove them.
2. **Email normalization**: Always use the manager to normalize emails.
3. **Password handling**: Use `set_password` or `set_unusable_password`. Never store raw passwords.
4. **Superusers**: Ensure all flags (`is_staff`, `is_superuser`, `is_active`, `email_verified`) are set correctly.
5. **Abstract vs Concrete**: Never register `AbstractBaseAccount` in `INSTALLED_APPS`; always use your subclass.

---

This document is focused on **customization and extension**, so anyone extending your package will know **exactly what is safe to override** and how to do it without breaking the base authentication logic.
