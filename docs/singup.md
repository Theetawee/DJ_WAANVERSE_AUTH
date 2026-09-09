# dj_waanverse_auth — Account Model & Signup Documentation

This document covers three things:

1. The `AbstractBaseAccount` model and its manager
2. The signup process (`SignupView`) end to end
3. How to extend the base account model with your own fields in a downstream project

---

## 1. The Base Account Model

### 1.1 Overview

`AbstractBaseAccount` is an **abstract** Django model built on top of `AbstractBaseUser` and `PermissionsMixin`. It is designed to support **three interchangeable identifiers** for authentication — `username`, `email_address`, and `phone_number` — where a user needs to supply only **one** of them to have a valid account. This is what allows the signup flow to accept email, phone, or username interchangeably depending on which identifiers your project has enabled.

Because it's abstract, it is never used directly. A concrete `Account` model in your project must subclass it:

```python
from dj_waanverse_auth.base_account import AbstractBaseAccount

class Account(AbstractBaseAccount):
    pass
```

And you must point Django at it:

```python
# settings.py
AUTH_USER_MODEL = "yourapp.Account"
```

### 1.2 Fields

| Field            | Type                               | Null/Blank | Unique | Notes                                                                                                                                                                                                             |
| ---------------- | ---------------------------------- | ---------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `username`       | `CharField(max_length=35)`         | Yes        | Yes    | Optional identifier. Stored as given by `create_user`/`create_superuser`; case handling and normalization is the caller's responsibility (the signup view lowercases it before saving).                           |
| `email_address`  | `EmailField(max_length=255)`       | Yes        | Yes    | Optional identifier. Normalized via `BaseUserManager.normalize_email` in the manager.                                                                                                                             |
| `phone_number`   | `CharField(max_length=20)`         | Yes        | Yes    | Optional identifier. Expected in **E.164 format** (e.g. `+256700123456`) — see §2.3.                                                                                                                              |
| `phone_region`   | `CharField(max_length=10)`         | Yes        | No     | ISO region code (e.g. `"UG"`) derived from the phone number. Only meaningful alongside a `phone_number`.                                                                                                          |
| `date_joined`    | `DateTimeField(auto_now_add=True)` | —          | —      | Set automatically on creation.                                                                                                                                                                                    |
| `is_active`      | `BooleanField`                     | —          | —      | **Defaults to `False`.** New accounts are inactive until your verification flow (OTP, email confirmation, etc.) explicitly sets this to `True`. Inactive users cannot authenticate via Django's default backends. |
| `is_staff`       | `BooleanField`                     | —          | —      | Defaults to `False`. Required for Django admin access.                                                                                                                                                            |
| `email_verified` | `BooleanField`                     | —          | —      | Defaults to `False`. Tracks whether the email identifier has been confirmed.                                                                                                                                      |
| `phone_verified` | `BooleanField`                     | —          | —      | Defaults to `False`. Tracks whether the phone identifier has been confirmed.                                                                                                                                      |

`last_login` and permission fields (`is_superuser`, `groups`, `user_permissions`) come from `AbstractBaseUser` / `PermissionsMixin` and are not redefined.

**Why no explicit indexes beyond `unique=True`?** Each unique field already gets a unique index from the database automatically — adding `db_index=True` or a `Meta.indexes` entry on the same field would just duplicate that index for no benefit. If you add your own non-unique filterable fields (see §3), index those explicitly if you query on them often.

### 1.3 `USERNAME_FIELD` and `REQUIRED_FIELDS`

```python
USERNAME_FIELD = "username"
REQUIRED_FIELDS = []
```

Django's auth system requires a `USERNAME_FIELD` even though this package supports multiple identifiers — it's mainly used by management commands (`createsuperuser`) and the admin, not by the OTP/multi-identifier login flow itself, which is handled by a custom authentication backend (`IdentifierOTPBackend`) elsewhere in the project.

**Implication:** `username` can be `None`. `createsuperuser` and Django admin lookups by natural key will only work smoothly for accounts that have a `username` set. If you create users purely via email or phone, be deliberate about how you handle admin access for those accounts.

### 1.4 Validation (`clean()`)

The model enforces these rules at the `full_clean()` level (called automatically by `AccountManager.create_user`):

1. **At least one identifier is required** — `username`, `email_address`, or `phone_number` must be present.
2. **`phone_region` requires `phone_number`** — you can't set a region without a phone number.
3. **`phone_verified=True` requires `phone_number`** — can't mark a phone verified with no phone.
4. **`email_verified=True` requires `email_address`** — can't mark an email verified with no email.

These are enforced regardless of which layer creates the object (manager, admin, serializer), as long as `full_clean()` / `save()` goes through the normal model validation path.

> **Known edge case:** Django distinguishes `NULL` from `''` (empty string) at the database level for uniqueness — multiple rows can have `NULL` in a unique column, but only one row can have `''`. The manager passes `None` by default, so this is safe through `create_user`/`create_superuser`. If you accept these fields through a `ModelForm`, DRF serializer, or the admin, make sure empty input is coerced to `None` rather than `''` before saving, or add that normalization into `clean()` yourself.

### 1.5 `AccountManager`

`create_user(username=None, email_address=None, phone_number=None, phone_region=None, password=None, **extra_fields)`

- Requires at least one of `username` / `email_address` / `phone_number` (raises `ValueError` otherwise — this is a pre-check before validation, so it fails fast with a clear message rather than a generic `ValidationError`).
- Normalizes `email_address` via `normalize_email` (lowercases the domain portion).
- Strips whitespace from `phone_number`.
- Sets a **usable password** if `password` is provided, otherwise calls `set_unusable_password()` — accounts can exist without a password (e.g. pure OTP-based accounts).
- Calls `full_clean()` before saving, so all `clean()` validation rules apply.

`create_superuser(...)` — same signature, plus:

- Forces `is_staff=True`, `is_superuser=True`, `is_active=True`, `email_verified=True` by default.
- Raises `ValueError` if `is_staff` or `is_superuser` are explicitly overridden to `False` in `extra_fields`.
- Delegates to `create_user` for actual creation, so all the same validation applies.

### 1.6 Permissions

`AbstractBaseAccount` does **not** override `has_perm` / `has_module_perms` — it relies entirely on `PermissionsMixin`, which means:

- `is_superuser=True` bypasses all permission checks.
- Otherwise, permissions are resolved through Django's normal auth backend chain (`django.contrib.auth.backends.ModelBackend` by default, plus any custom backends you've configured) via `groups` and `user_permissions`.
- `is_staff` alone does **not** grant permissions — it only gates access to the Django admin UI. If you want a simplified "staff = full access" model instead of granular permissions, that decision needs to be made explicitly in your own backend or view logic, not by overriding these methods on the model.

---

## 2. The Signup Process (`SignupView`)

### 2.1 Endpoint behavior

`SignupView` is a DRF `APIView` (`permission_classes = [AllowAny]`) exposing `POST` only. Request body:

```json
{
    "identifier": "wave@example.com",
    "password": "StrongPassword123!"
}
```

High-level flow:

1. If `auth_config.disable_signup` is `True` → `403 Forbidden`.
2. `identifier` and `password` are both required → `400` if either is missing.
3. `identifier` is stripped of surrounding whitespace.
4. The identifier's **type** is detected (`get_identifier_type`) based on which identifier kinds are enabled in config and which shape the string matches.
5. The request is routed to the matching handler: `handle_signup_email`, `handle_signup_phone`, or `handle_signup_username`.
6. Each handler validates, checks for duplicates, creates the account via `AccountManager.create_user`, and returns `201` on success.

On success, all handlers return:

```json
{ "msg": "Account created successfully." }
```

with `201 Created`. Newly created accounts have `is_active=False` — activation is expected to happen via a separate OTP/verification flow, not at signup time.

### 2.2 Identifier type detection (`get_identifier_type`)

Order of evaluation:

1. **Email** — checked first if `"email"` is in `auth_config.authentication_identifiers`, using Django's `validate_email`.
2. **Phone** — checked next if `"phone"` is enabled, using `phonenumbers` to confirm it's a valid, parseable international number.
3. **Username** — the **fallback**. If `"username"` is enabled and neither email nor phone matched, the identifier is treated as a username regardless of its actual shape. This means an email-shaped string will be routed to the username handler (and rejected there by the character-set regex) if email is disabled but username is enabled.
4. If nothing matches → `None`, and the view returns `400` with `"Please provide a valid identifier."`.

**This ordering matters.** A string like `+256700123456` will never reach the username handler if phone is enabled, because phone is checked before the username fallback. But if you disable phone and enable only email + username, phone numbers will be funneled into the username validator and rejected for containing invalid characters — not because of a "not a valid phone" message.

### 2.3 Email signup (`handle_signup_email`)

1. Validates format via `validate_email`.
2. Lowercases and strips the address.
3. Extracts the domain and checks it against `auth_config.allowed_email_domains` (if set, acts as an **allowlist** — only these domains may register).
4. Checks the full address against `auth_config.blacklisted_emails`.
5. Checks the domain against `auth_config.blacklisted_email_domains`.
6. Checks for an existing account with `email_address__iexact` (case-insensitive duplicate check).
7. Creates the account with `email_address` + `password`.

### 2.4 Phone signup (`handle_signup_phone`)

Phone numbers **must include the country code** (leading `+`), e.g. `+256700123456`.

1. `normalize_phone` (static method) validates and normalizes the number:
    - Confirms it starts with `+`.
    - Parses with `phonenumbers.parse(phone, None)` — the `None` region means it relies entirely on the `+`-prefixed country code; there's no fallback default region.
    - Confirms `phonenumbers.is_valid_number()`.
    - Formats to **E.164** (`phonenumbers.PhoneNumberFormat.E164`) for consistent storage.
    - Derives `phone_region` (e.g. `"UG"`) from the parsed number.
    - Raises `ValueError` (with a user-facing message) on any failure — the view converts this to a `400`.
2. Checks for an existing account with an exact `phone_number` match (not `iexact`, since E.164 numbers have a canonical casing-free format).
3. Creates the account with `phone_number`, `phone_region`, and `password`.

### 2.5 Username signup (`handle_signup_username`)

1. Strips and lowercases the username.
2. Length must be 3–30 characters.
3. Must match `^[a-zA-Z0-9_]+$` — letters, numbers, underscores only (no spaces, hyphens, dots, or `@`).
4. Checked against `auth_config.blacklisted_usernames` (case-insensitive).
5. Checked for an existing account with `username__iexact`.
6. Creates the account with `username` + `password`.

### 2.6 Configuration reference

Refer to [`auth_config`](./settings.md) for configuration options.

### 2.7 Error responses

All error responses follow the same shape:

```json
{ "msg": "<human-readable reason>" }
```

| Status | Scenario                                                                                                                          |
| ------ | --------------------------------------------------------------------------------------------------------------------------------- |
| `400`  | Missing identifier/password, invalid format, disallowed domain, blacklisted value, duplicate account, no matching identifier type |
| `403`  | Signup disabled via config                                                                                                        |
| `201`  | Account created                                                                                                                   |

There is currently no field-level error structure (e.g. DRF's typical `{"identifier": [...]}`) — errors are flat, single-message responses under `"msg"`. Keep this in mind if you're building a frontend that expects per-field validation errors; you'll need to key off the message string or extend the view to return structured errors.

---

## 3. Extending the Base Account Model

The whole point of `AbstractBaseAccount` being abstract is that you subclass it in your own app and add whatever fields your project needs, without touching the package itself.

### 3.1 Basic extension

```python
# yourapp/models.py
from django.db import models
from dj_waanverse_auth.models import AbstractBaseAccount


class Account(AbstractBaseAccount):
    display_name = models.CharField(max_length=100, blank=True)
    avatar_url = models.URLField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    country = models.CharField(max_length=2, blank=True)  # ISO 3166-1 alpha-2

    def __str__(self):
        return self.display_name or super().__str__()
```

```python
# settings.py
AUTH_USER_MODEL = "yourapp.Account"
```

Then run:

```bash
python manage.py makemigrations yourapp
python manage.py migrate
```

**Important:** `AUTH_USER_MODEL` must be set **before your first migration ever runs** on a given database. Swapping the user model on a project that already has migrations applied against a different model requires a manual data migration — it isn't a drop-in change later.

### 3.2 Adding your own manager methods (recommended pattern)

If you need custom fields to be part of user creation (e.g. `country` required at signup), extend `AccountManager` rather than overriding `create_user` from scratch — call `super()` so you keep the identifier validation and `full_clean()` behavior:

```python
from dj_waanverse_auth.models import AccountManager

class CustomAccountManager(AccountManager):
    def create_user(self, *, country=None, **kwargs):
        user = super().create_user(**kwargs)
        if country:
            user.country = country
            user.save(update_fields=["country"])
        return user


class Account(AbstractBaseAccount):
    country = models.CharField(max_length=2, blank=True)
    objects = CustomAccountManager()
```

### 3.3 Adding your own `clean()` rules

If your new fields need cross-field validation (similar to the phone/email/verification rules already on the base model), override `clean()` and call `super().clean()` first so the base rules still run:

```python
class Account(AbstractBaseAccount):
    date_of_birth = models.DateField(blank=True, null=True)
    is_minor_account = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        from datetime import date

        if self.date_of_birth and self.is_minor_account:
            age = (date.today() - self.date_of_birth).days // 365
            if age >= 18:
                raise ValidationError(
                    "is_minor_account cannot be True for a user 18 or older."
                )
```

### 3.4 Adding indexes for your own fields

Unlike `username` / `email_address` / `phone_number` (already uniquely indexed by the base model), any new **non-unique** field you add that you'll filter or sort on frequently should get its own index explicitly:

```python
class Account(AbstractBaseAccount):
    country = models.CharField(max_length=2, blank=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["country", "date_joined"]),
        ]
```

### 3.5 Things to watch for when extending

- **Don't re-declare `username`, `email_address`, or `phone_number`.** They're already defined on the abstract base; redeclaring them in the subclass will conflict with the inherited fields.
- **Signup handlers don't know about your new fields.** `SignupView` only ever sets `username`/`email_address`/`phone_number`/`phone_region`/`password`. If you add required fields (e.g. `country` in §3.2), either give them a sensible default, make them nullable, or override/extend the signup handlers to collect and pass them through — otherwise `full_clean()` may fail on account creation if you also add a "required" validation rule for them.
- **`is_active` stays `False` by default** regardless of what you add — make sure whatever activation/verification flow you build (OTP, email confirmation link, etc.) explicitly flips it, or accounts will be permanently unable to authenticate via the default backends.
- **Admin registration** — if you add an `AccountAdmin`, remember `username` can be `None`; guard any admin `list_display`/`search_fields` logic that assumes it's always populated.
- **Migrations** — every time you add a field to your concrete `Account` model, run `makemigrations` against **your app**, not the package. The package's abstract model has no migrations of its own to manage.

---

## 4. Quick Reference: What's Enforced Where

| Rule                                    | Enforced in                                                                                                                    |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| At least one identifier present         | `AbstractBaseAccount.clean()`                                                                                                  |
| `phone_region` requires `phone_number`  | `AbstractBaseAccount.clean()`                                                                                                  |
| Verified flags require their identifier | `AbstractBaseAccount.clean()`                                                                                                  |
| Email format                            | `SignupView.handle_signup_email` (view-level, before hitting the model)                                                        |
| Email allowlist / blacklist             | `SignupView.handle_signup_email` + `auth_config`                                                                               |
| Phone format (E.164, valid)             | `SignupView.normalize_phone` (view-level)                                                                                      |
| Username length / charset / blacklist   | `SignupView.handle_signup_username` (view-level)                                                                               |
| Duplicate identifiers                   | `SignupView` handlers, via `__iexact` (email/username) or exact match (phone) — **not** a DB-level case-insensitive constraint |
| Password required at signup             | `SignupView.post` (the model itself allows no password via `set_unusable_password()`)                                          |
| Account activation                      | **Not handled by signup** — expected to be a separate flow (OTP/verification) that sets `is_active=True`                       |
