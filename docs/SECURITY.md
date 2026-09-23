# Security Design

This document explains the *why* behind decisions that would
otherwise look arbitrary in a code review — each one was a deliberate
tradeoff, not a default.

## Enumeration resistance

Login, verify, and password-reset-request all return **identical**
responses (status code and message body) regardless of whether the
account exists, the password was wrong, or the identifier shape was
unrecognized. Login additionally runs a dummy password hash
(`Account().set_password(password)`) on the no-account path — without
it, a nonexistent-account response would measurably return faster
than a wrong-password one, a textbook timing side-channel.

**Signup is the one deliberate exception** — it returns
`"Account already exists."` for a duplicate identifier. That's an
accepted, narrower tradeoff (better signup UX) made once, consciously
— not a gap in the general pattern.

Unverified-account status (`403` on login) is revealed **only after**
the password check passes — so it can't be used to probe which
identifiers belong to unverified accounts without already knowing
the password.

Session revocation (`POST /sessions/<uuid>/revoke/`) returns the same
`404` for "doesn't exist" and "belongs to someone else," for the same
reason.

## Refresh rotation and reuse detection

Every refresh call issues a brand-new refresh token and invalidates
the one presented — only the hash of the *current* valid refresh
token is stored per session (`Session.refresh_token_hash`), never the
raw value.

If a refresh token that's already been superseded gets presented
again, that's treated as reuse — meaning a stolen token being used
*alongside* the legitimate client's own rotation, not just an
expired token being retried. The response is to **revoke the whole
session**, not just reject the one request: a legitimate client would
never present an already-rotated token, so this is a strong compromise
signal.

## Revocation latency

`JWTAuthentication` validates access tokens purely by signature,
expiry, and account state (exists, active) — it does **not** check
`Session.is_revoked` on every request. That would mean a database
hit on every authenticated API call, defeating the point of using
stateless JWTs at all.

The consequence: revoking a session (logout, "revoke this device," a
password reset) stops future **refreshes** immediately, but any
access token already issued for that session stays valid until its
own short TTL naturally expires. `ACCESS_TOKEN_LIFETIME` is therefore
the practical upper bound on how "instant" revocation actually is —
keep it short if this matters to your threat model.

## Cookies and CSRF

Access and refresh tokens are httponly cookies for web clients
specifically to block XSS-based token theft (`document.cookie` can't
read them). That protection creates a different problem: DRF skips
CSRF enforcement by default for any authentication class other than
`SessionAuthentication` — an assumption that's simply wrong once your
custom auth class is cookie-based too.

The fix is a hand-rolled **double-submit cookie**, independent of
Django's own `CsrfViewMiddleware`/`CSRF_*` settings (they don't share
any state — see the note in `SETTINGS.md` if you're also running
Django admin, which uses Django's native CSRF system separately). A
`csrf_token` cookie (readable by JS — deliberately *not* httponly) is
reissued on every token-issuing response; the client echoes it back
as `X-CSRF-Token` on every unsafe-method request. The server checks
the two match via constant-time comparison.

**Critically, this only applies when the auth token itself came from
a cookie.** A mobile client authenticating via `Authorization: Bearer`
never needs a CSRF token at all — a cross-site attacker's page can't
make a victim's browser attach an arbitrary header the way it can
make the browser attach an ambient cookie. `enforce_csrf_if_cookie_sourced`
is a no-op for bearer-sourced requests, checked by *source*, not by
endpoint.

Enforced on: `RefreshView`, `LogoutView`, and — via
`JWTAuthentication` itself — any future `IsAuthenticated` view on an
unsafe method with a cookie-sourced access token. **Not** enforced on
signup/login/verify/password-reset, since those are `AllowAny` with
`authentication_classes = []` — there's no prior cookie to CSRF-protect
at that point in the flow.

`COOKIE_SECURE` defaults to `not DEBUG` specifically because modern
browsers treat `localhost` as a trustworthy origin for `Secure`
cookies even over plain HTTP, but a LAN IP (testing from a phone
against a laptop dev server) is not — the default handles the common
dev case without needing to remember to flip a flag.

## IP trust boundary

`IPAddressMiddleware` attaches `request.ip_address`, used for session
metadata (`Session.ip_address`) and Turnstile's `remoteip` — it is
**not** a security gate; unlike the deleted `ClientIPMiddleware`, it
never rejects a request.

Forwarded headers (`X-Forwarded-For`, `CF-Connecting-IP`) are only
trusted when the *immediate* connecting peer (`REMOTE_ADDR`) is
inside a known-trusted range — otherwise a request hitting Django
directly could set its own `X-Forwarded-For` and have it accepted at
face value. Two important, non-obvious details:

- When the peer is genuinely Cloudflare, `CF-Connecting-IP` is
  preferred over `X-Forwarded-For` — the former is Cloudflare's own
  direct assertion; the latter can carry earlier, client-supplied
  hops Cloudflare doesn't strip.
- When falling back to `X-Forwarded-For` (peer is a trusted local
  proxy, not Cloudflare), the **last** entry is used, not the first —
  a well-behaved proxy *appends* the address it saw rather than
  replacing the header, so earlier entries can be attacker-supplied.

`TRUST_CLOUDFLARE_ONLY` (default: `not DEBUG`) controls whether
localhost is *also* trusted as a forwarder, for single-local-proxy
setups (e.g. nginx on the same box). In production, confirm whatever
reverse proxy sits in front of Django actually **overwrites**
`X-Forwarded-For` with the real client IP rather than blindly passing
through whatever the client sent — this middleware's trust boundary
is only as good as that upstream behavior.

## Turnstile

Verification **fails closed**: a network error, timeout, or
non-2xx response from Cloudflare's siteverify endpoint returns
`False`, not `True`. A Cloudflare outage means signup/login briefly
stop working rather than silently losing bot protection.
`TURNSTILE_ENABLED=True` with no secret key fails `manage.py check`
rather than silently no-op'ing.

## Throttling

Every unauthenticated, state-changing endpoint has both an IP-keyed
and (where applicable) identifier-keyed throttle. Identifier rates
are deliberately tighter than IP rates for the same action — a single
email/phone is a much more precise abuse signal than an IP, which can
represent an entire shared network of legitimate users.

`VerifyAccountView` and `PasswordResetConfirmView` only carry an
IP-keyed throttle, not an identifier one — per-code guessing is
already capped by `MAX_ATTEMPTS` at the model level (5 attempts, then
locked out until a fresh code is issued); the IP throttle's job is
slowing an attacker rotating across many different accounts from one
IP, a different threat than guessing one code repeatedly.

Session-management endpoints use DRF's `UserRateThrottle` (keyed on
`request.user.pk`), not the IP/identifier throttles — the threat
model there is "what can an authenticated user's compromised token
do," not unauthenticated flooding.

`LogoutView` is intentionally **not** throttled — it can't be abused
for credential stuffing or enumeration, and throttling it risks
locking a legitimate user out of the one action whose entire job is
letting them leave.

## Session isolation

`VerificationCode` and `PasswordResetCode` are deliberately **separate
tables**, despite sharing the same shape (hashed code + link token,
dual expiry, attempt lockout, invalidate-previous-on-reissue). Sharing
one table would mean requesting a password reset could silently
invalidate a pending signup-verification code for the same account,
or vice versa — correct behavior *within* one purpose, wrong *across*
two unrelated ones.
