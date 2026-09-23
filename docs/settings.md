# Settings Reference

All settings live under one dict in your project's `settings.py`:

```python
WAANVERSE_AUTH_CONFIG = {
    "KEY_NAME": value,
    ...
}
```

Each key is exposed to the package's own code as a lowercased
attribute on `auth_config` (e.g. `TURNSTILE_ENABLED` →
`auth_config.turnstile_enabled`). **This doc calls out every place
that mapping is currently broken** — a setting whose code path reads
a different attribute name than what's declared here will silently
do nothing, the same way `TURNSTILE_ENABLED` silently did nothing
under its old name (`ENABLE_TURNSTILE`) until that got caught and
fixed. Treat every ⚠️ below as a real bug to fix, not a documentation
nitpick.

**Status key:**
✅ implemented and confirmed working · ⚠️ name mismatch, currently a
no-op · 🚧 declared in the schema, not wired into any code path yet

---

## Core

| Key | Type | Default | Status |
|---|---|---|---|
| `DISABLE_SIGNUP` | `bool` | `False` | ✅ |
| `AUTHENTICATION_IDENTIFIERS` | `list[str]` | — (required) | ✅ |

`AUTHENTICATION_IDENTIFIERS` controls which identifier types signup,
login, verification, and password reset will recognize. Valid
values: `"email"`, `"phone"`, `"username"`. Username has no
verification channel — enabling it re-activates dormant signup/login
code paths but is not recommended without also building a
verification story for it. An empty list, or a value outside these
three, fails `manage.py check` (`dj_waanverse_auth.E002` /
`dj_waanverse_auth.E003`).

## Turnstile (bot protection)

| Key | Type | Default | Status |
|---|---|---|---|
| `TURNSTILE_ENABLED` | `bool` | `False` | ✅ |
| `TURNSTILE_SECRET_KEY` | `str` | `None` | ✅ |

`TURNSTILE_ENABLED = True` with no secret key fails `manage.py check`
(`dj_waanverse_auth.E001`) rather than silently doing nothing.
Verification fails **closed** on any network error talking to
Cloudflare's siteverify endpoint — a timeout or outage rejects the
request rather than letting it through.

## Notifications

| Key | Type | Default | Status |
|---|---|---|---|
| `SMS_SENDER` | `str` (dotted path) | `None` → console logger | ✅ |
| `ACCOUNT_VERIFICATION_EMAIL_SUBJECT` | `str` | — | 🚧 |
| `ACTIVATION_FRONTEND_URL` | `str` | — | ⚠️ |

`SMS_SENDER` is a dotted import path to a function with signature
`(phone_number: str, message: str) -> None`, resolved fresh on every
call (not cached) so `override_settings` in tests works correctly.
With nothing configured, SMS "sends" are logged to the console —
fine for development, not a real delivery mechanism.

`ACCOUNT_VERIFICATION_EMAIL_SUBJECT` is declared but the email
subject is currently hardcoded (`"Verify your account"`) in
`notifications/email.py` — setting this key does nothing yet.

`ACTIVATION_FRONTEND_URL` has a real mismatch: the code currently
reads `auth_config.frontend_url`, not `auth_config.activation_frontend_url`.
**Fix before relying on this** — either rename the code's attribute
access to match the schema, or rename the schema key to `FRONTEND_URL`
to match the code. Until one side changes, setting
`ACTIVATION_FRONTEND_URL` has no effect and verification links will
build against whatever (likely broken) default `frontend_url`
resolves to.

## Verification codes

| Key | Type | Default | Status |
|---|---|---|---|
| `VERIFICATION_CODE_LENGTH` | `int` | — | 🚧 |
| `VERIFICATION_CODE_TTL` | `timedelta` | — | 🚧 |
| `VERIFICATION_LINK_TTL` | `timedelta` | — | 🚧 |
| `VERIFICATION_MAX_ATTEMPTS` | `int` | — | 🚧 |

None of these four are currently read anywhere. `VerificationCode`
and `PasswordResetCode` both use hardcoded module-level constants in
`models.py` instead: a 6-digit code, 15-minute code TTL, 24-hour link
TTL, and 5 max attempts before lockout. **This is the single biggest
gap between this schema and the actual implementation.** If
per-project configurability of these values matters, `models.py`
needs to read them from `auth_config` (with the current hardcoded
values as fallback defaults) rather than the constants being fixed
at import time.

## Email restrictions

| Key | Type | Default | Status |
|---|---|---|---|
| `BLACKLISTED_EMAILS` | `list[str]` | `[]` | ✅ |
| `ALLOWED_EMAIL_DOMAINS` | `list[str]` | `[]` (no restriction) | ✅ |
| `BLACKLISTED_EMAIL_DOMAINS` | `list[str]` | `[]` | ✅ |

All three are checked case-insensitively in `SignupView`. An empty
`ALLOWED_EMAIL_DOMAINS` means no domain restriction at all — it's an
allowlist, not a required field.

## JWT signing

| Key | Type | Default | Status |
|---|---|---|---|
| `PUBLIC_KEY_PATH` | `str`/`Path` | — (required) | ✅ |
| `PRIVATE_KEY_PATH` | `str`/`Path` | — (required) | ✅ |
| `JWT_ISSUER` | `str` | `"dj_waanverse_auth"` | ✅ |
| `ACCESS_TOKEN_LIFETIME` | `timedelta` | `30 minutes` | ✅ |
| `REFRESH_TOKEN_LIFETIME` | `timedelta` | `30 days` | ✅ |

Keys are read from disk and cached in-process (`functools.lru_cache`)
— a key file changed on disk after process start won't take effect
without a restart. Algorithm is always RS256, explicitly pinned on
decode (never trusts the token's own `alg` header) — this isn't
configurable and shouldn't be.

`ACCESS_TOKEN_LIFETIME` is the practical upper bound on how long a
revoked session's already-issued access token stays valid — see
[SECURITY.md](./SECURITY.md#revocation-latency).

## Cookies

| Key | Type | Default | Status |
|---|---|---|---|
| `ACCESS_TOKEN_COOKIE_NAME` | `str` | `"access_token"` | ✅ |
| `REFRESH_TOKEN_COOKIE_NAME` | `str` | `"refresh_token"` | ✅ |
| `COOKIE_PATH` | `str` | `"/"` | ✅ |
| `COOKIE_DOMAIN` | `str \| None` | `None` | ✅ |
| `COOKIE_SAMESITE_POLICY` | `str` | `"Lax"` | ⚠️ |
| `COOKIE_SECURE` | `bool` | `not settings.DEBUG` | ✅ |
| `CSRF_COOKIE_NAME` | `str` | `"csrf_token"` | ⚠️ |

`COOKIE_SAMESITE_POLICY` is a real mismatch — the code reads
`auth_config.cookie_samesite`, not `cookie_samesite_policy`. Same
fix needed as `ACTIVATION_FRONTEND_URL` above: align one side with
the other.

`CSRF_COOKIE_NAME` is hardcoded as a module constant
(`CSRF_COOKIE_NAME = "csrf_token"`) in `utils/csrf.py`, not read from
`auth_config` at all — setting this key currently does nothing.

`COOKIE_SECURE`'s default follows `DEBUG` specifically so local
development over plain HTTP still works (modern browsers treat
`localhost` as a trustworthy origin even for `Secure` cookies, but a
LAN IP like `192.168.x.x` does not) — see
[SECURITY.md](./SECURITY.md#cookies-and-csrf).

## IP resolution

| Key | Type | Default | Status |
|---|---|---|---|
| `TRUST_CLOUDFLARE_ONLY` | `bool` | `not settings.DEBUG` | ✅ |

Governs whether `IPAddressMiddleware` also trusts a local reverse
proxy (`127.0.0.1`/`::1`) as a source of forwarded-header
information, or only Cloudflare's published ranges. See
[SECURITY.md](./SECURITY.md#ip-trust-boundary) for what this
middleware does and does not protect against.

## Admin

| Key | Type | Default | Status |
|---|---|---|---|
| `ENABLE_ADMIN_PANEL` | `bool` | `False` | ⚠️ |

The code currently reads `auth_config.enable_admin`, not
`auth_config.enable_admin_panel` — this key does nothing until that's
fixed. Once corrected, this gates whether `Session`,
`VerificationCode`, and `PasswordResetCode` get registered in Django
admin at all (via `register_admin()` in `admin.py`) — not just
whether they're visible, but whether they're registered.

## Reserved / not yet used

| Key | Type | Status |
|---|---|---|
| `SIGNUP_SERIALIZER_CLASS` | `str` (dotted path) | 🚧 |

`SignupView` currently does its own manual field validation rather
than using a DRF serializer at all — this key has no consumer yet.
Treat it as reserved for a future refactor, not a currently-supported
extension point.

---

## Before shipping: fix the ⚠️ rows

Four settings are silent no-ops right now due to a name mismatch
between this schema and the code: `ACTIVATION_FRONTEND_URL`,
`COOKIE_SAMESITE_POLICY`, `CSRF_COOKIE_NAME`, `ENABLE_ADMIN_PANEL`.
None of these fail loudly — a project setting them expecting an
effect gets none, with no error. Worth a dedicated pass reconciling
`config/settings.py`'s attribute names against this schema before
treating any of the four as reliable.
