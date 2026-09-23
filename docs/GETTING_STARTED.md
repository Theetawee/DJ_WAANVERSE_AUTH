# Getting Started

## 1. Install and register the app

```bash
pip install dj_waanverse_auth
```

```python
INSTALLED_APPS = [
    ...,
    "dj_waanverse_auth",
    "rest_framework",
]
```

## 2. Point auth at your user model

The package expects your `AUTH_USER_MODEL` to expose
`email_address`, `phone_number`, `phone_region`, `is_active`,
`email_verified`, and `phone_verified`. `username` is supported but
optional given the identifier restriction below.

```python
AUTH_USER_MODEL = "accounts.Account"
```

## 3. DRF settings

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "dj_waanverse_auth.authentication.JWTAuthentication",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "signup-ip": "10/hour",
        "signup-identifier": "5/hour",
        "login-ip": "20/hour",
        "login-identifier": "8/hour",
        "verification-request-ip": "10/hour",
        "verification-request-identifier": "5/hour",
        "verify-account-ip": "30/hour",
        "password-reset-request-ip": "10/hour",
        "password-reset-request-identifier": "5/hour",
        "password-reset-confirm-ip": "30/hour",
        "refresh-ip": "60/hour",
        "session-actions": "100/hour",
    },
}
```

Every rate is optional — an omitted scope means DRF applies no limit
for it. See [SECURITY.md](./SECURITY.md#throttling) for the reasoning
behind these specific numbers.

## 4. Middleware

```python
MIDDLEWARE = [
    ...,
    "dj_waanverse_auth.middleware.IPAddressMiddleware",
]
```

This is informational IP resolution (`request.ip_address`), not a
security gate — see [SECURITY.md](./SECURITY.md#ip-trust-boundary)
for what it does and doesn't protect against.

## 5. CORS (if your frontend is a separate origin)

The CSRF header this package uses (`X-CSRF-Token`) is not in
`django-cors-headers`' default allowed header list — without this,
the browser silently strips it and every cookie-authenticated
mutating request will 403:

```python
from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = list(default_headers) + ["x-csrf-token"]
CORS_ALLOW_CREDENTIALS = True
```

## 6. RSA keypair for JWT signing

Tokens are signed with RS256. Generate a keypair once per environment
— **never commit these to version control**:

```bash
openssl genrsa -out private_key.pem 2048
openssl rsa -in private_key.pem -pubout -out public_key.pem
```

```python
WAANVERSE_AUTH_CONFIG = {
    "PRIVATE_KEY_PATH": BASE_DIR / "secrets/private_key.pem",
    "PUBLIC_KEY_PATH": BASE_DIR / "secrets/public_key.pem",
}
```

## 7. URLs

```python
# your project's urls.py
urlpatterns = [
    ...,
    path("auth/", include("dj_waanverse_auth.urls")),
]
```

## 8. Migrations

```bash
python manage.py makemigrations dj_waanverse_auth
python manage.py migrate
```

> Run `makemigrations --check --dry-run` in CI. If this package's
> models (`Session`, `VerificationCode`, `PasswordResetCode`) ever
> change without a matching migration file committed, this catches
> it before it reaches anyone running `migrate` for real.

## 9. Minimal working config

```python
WAANVERSE_AUTH_CONFIG = {
    "AUTHENTICATION_IDENTIFIERS": ["email", "phone"],
    "PRIVATE_KEY_PATH": BASE_DIR / "secrets/private_key.pem",
    "PUBLIC_KEY_PATH": BASE_DIR / "secrets/public_key.pem",
}
```

Everything else has a sensible default — see
[SETTINGS.md](./SETTINGS.md) for the full list and what each default
actually is.

## 10. Sanity check

```bash
python manage.py check
```

This runs the package's own system checks (`dj_waanverse_auth.E001`
–`E003`) — they'll fail loudly if, for example, Turnstile is enabled
with no secret key, or no identifier type is enabled at all.
