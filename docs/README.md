# dj_waanverse_auth — Documentation

A Django + Django REST Framework authentication package built around a
single flexible `identifier` field (email, phone, or username),
RS256 JWT sessions delivered via httponly cookies (with Bearer-token
support for mobile), and the account lifecycle a real product needs:
signup, verification, login, logout, refresh, password reset, and
session management.

## Contents

- **[GETTING_STARTED.md](./GETTING_STARTED.md)** — installation, required
  setup (RSA keys, middleware, migrations), and a minimal working config.
- **[SETTINGS.md](./SETTINGS.md)** — every `WAANVERSE_AUTH_CONFIG` key,
  what it does, its default, and — importantly — which ones are
  actually wired into the code today vs. declared but not yet
  implemented.
- **[AUTHENTICATION.md](./AUTHENTICATION.md)** — the request/response
  shape of every auth endpoint: signup, verify, login, refresh,
  logout, password reset, sessions.
- **[SECURITY.md](./SECURITY.md)** — the design decisions that matter
  for a security review: cookie/CSRF model, token rotation and reuse
  detection, IP trust boundary, enumeration resistance, Turnstile,
  throttling.

## Design at a glance

- **One identifier, not three separate fields.** Signup, login,
  verification, and password reset all accept a single `identifier`
  value and detect whether it's an email or a phone number. Username
  is supported in the code but disabled by default — it has no
  verification channel, so it's off until a project explicitly
  re-enables it via `AUTHENTICATION_IDENTIFIERS`.
- **Tokens are cookies first, Bearer second.** `access_token` and
  `refresh_token` are set as httponly cookies for web clients. A
  mobile client identifies itself with `X-Client-Type: mobile` and
  receives the same tokens in the JSON body instead, for storage in
  secure device storage rather than a cookie jar.
- **State changes are not blocked on login succeeding.** Verifying an
  account or resetting a password commits regardless of whether the
  subsequent auto-login token issuance succeeds. A token-issuance
  failure just means the user logs in manually next — it never rolls
  back a verification or a password change that already happened.
