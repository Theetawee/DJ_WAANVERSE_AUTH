# Authentication Flows

All endpoints live under whatever prefix you mount
`dj_waanverse_auth.urls` at (`/auth/` in the examples below). All
POST bodies are JSON.

## Signup

```
POST /auth/signup/
{ "identifier": "wave@example.com", "password": "..." }
```

Detects whether `identifier` is an email or phone automatically
(username is disabled by default — see
[SETTINGS.md](./SETTINGS.md#core)). On success, creates an account
with `is_active=False` and returns `201` — **no tokens are issued at
signup**. The account cannot log in until verified.

Rejections: missing/oversized fields, unrecognized identifier shape,
blacklisted/non-allowed email domain, blacklisted email, identifier
already registered (`"Account already exists."` — this endpoint does
reveal existence; see
[SECURITY.md](./SECURITY.md#enumeration-resistance) for why that's a
different tradeoff than login/verify/reset), weak password (runs
Django's configured `AUTH_PASSWORD_VALIDATORS`).

If `TURNSTILE_ENABLED`, a `turnstile_token` field is also required.

## Request verification (send a code or link)

```
POST /auth/verify/request/
{ "identifier": "wave@example.com", "delivery": "code" }
```

`delivery` is `"code"` or `"link"` (default `"code"`). Phone
identifiers only support `"code"` — `"link"` is rejected before any
lookup happens. Always responds `200` with an identical generic
message regardless of whether the account exists, is already
verified, or genuinely got a fresh code sent — this endpoint is
deliberately non-enumerable, more so than signup, since repeatedly
probing it can trigger real SMS/email sends.

Issuing a new code invalidates any previous unused one for that
account — only the latest is ever valid.

## Verify account (confirm a code or link)

```
POST /auth/verify/
{ "identifier": "wave@example.com", "access": "482913" }
```

`access` is either the 6-digit code or the link token — the endpoint
infers which by shape (all-digit, 6 characters → treated as a code).
On success: account flips to `is_active=True`, the matching
`email_verified`/`phone_verified` flag is set, the code is marked
used, and — **as a separate step, not gated on the state change
above** — the account is auto-logged-in (see
[README.md](./README.md#design-at-a-glance)). Cookies are set the
same way login sets them.

Failure modes: wrong code/token increments an attempt counter (5
attempts, then locked out until a fresh code is requested); expired;
already used; phone identifier presented with a link-shaped `access`.
All return the same generic `"invalid or expired"` message — never
distinguishing *why*.

## Login

```
POST /auth/login/
{ "identifier": "wave@example.com", "password": "..." }
```

`200` + cookies on success. `400` with an identical generic message
for wrong password, nonexistent account, or an unrecognized
identifier shape — genuinely indistinguishable, including matched
response *timing* (a dummy password hash runs even when no account
was found, so a nonexistent-account response doesn't return
suspiciously faster than a wrong-password one).

`403` specifically for an unverified account — but only ever reached
*after* the password check passes, so this status can't be used to
probe whether an identifier belongs to an unverified account without
already knowing its password.

If `TURNSTILE_ENABLED`, `turnstile_token` is required here too.

## Refresh

```
POST /auth/refresh/
```

No body needed — reads the refresh token from the `refresh_token`
cookie, falling back to `Authorization: Bearer <token>` if no cookie
is present (the mobile path). Rotates the token: issues a new
access/refresh pair for the same session and invalidates the one
presented.

**Reuse detection:** presenting an already-rotated (superseded)
refresh token doesn't just fail this one request — it revokes the
*entire session*. See
[SECURITY.md](./SECURITY.md#refresh-rotation-and-reuse-detection) for
why.

`401` on any failure (expired, malformed, revoked session, reuse
detected) and clears auth cookies on the way out, so a dead session
doesn't linger client-side.

Cookie-sourced refresh calls require a CSRF header — see
[SECURITY.md](./SECURITY.md#cookies-and-csrf).

## Logout

```
POST /auth/logout/
```

Same token lookup as refresh. Deliberately **does not require a
valid access token or `IsAuthenticated`** — the whole point is that
logout still works when the access token is already dead, which is
one of the most common reasons someone hits logout at all. Revokes
the session behind the refresh token if it's still valid; if the
token is garbage, expired, or already gone, logout is a harmless
no-op. Either way: `200`, cookies cleared, best-effort by design.

## Password reset — request

```
POST /auth/password-reset/request/
{ "identifier": "wave@example.com", "delivery": "code" }
```

Same shape as verification-request, same generic non-enumerable
response. Only `is_active=True` accounts are eligible — an
unverified account has no meaningful "forgot password" state; it
should go through account verification instead.

## Password reset — confirm

```
POST /auth/password-reset/
{ "identifier": "wave@example.com", "access": "482913", "new_password": "..." }
```

On success: the code is marked used, the password is changed, **every
existing session for the account is revoked** (a password reset is a
security-relevant event — this kills any session an attacker might
be holding), and — as a separate step — the account is
auto-logged-in with a fresh session for the current request. Runs
Django's password validators against `new_password` before
committing anything.

Same generic-error and lockout behavior as account verification.

## Sessions (requires a valid access token)

```
GET  /auth/sessions/
POST /auth/sessions/<uuid>/revoke/
POST /auth/sessions/revoke-others/
```

`GET /sessions/` lists the authenticated account's active
(non-revoked) sessions — `user_agent`, `ip_address`, `created_at`,
`last_used_at`, and `is_current` (matched against the session id
embedded in the presented access token).

`POST /sessions/<uuid>/revoke/` revokes one specific session. Always
`404` — never `403` — whether the id doesn't exist or belongs to a
different account; those two cases are structurally indistinguishable
by design, so this endpoint can't be used to probe which session ids
exist for other users.

`POST /sessions/revoke-others/` revokes every other active session
for the account, leaving the one making the request untouched — "log
out all other devices."

## Web vs. mobile

Every token-issuing response (signup — no, signup issues none; verify,
login, refresh, password-reset-confirm) goes through the same helper.
By default, tokens are set as httponly cookies and **never** included
in the JSON body — that's the point of httponly. A client that sends
`X-Client-Type: mobile` receives the raw tokens in the response body
*in addition to* the cookies (harmless for a native app that ignores
`Set-Cookie`), for storage in secure device storage instead of a
cookie jar.
