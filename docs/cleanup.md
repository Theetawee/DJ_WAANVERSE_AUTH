# Authentication Cleanup Commands

`dj-waanverse-auth` provides management commands for removing expired, revoked, and otherwise no-longer-needed authentication records from the database.

These commands are designed to prevent authentication tables from growing indefinitely while keeping cleanup operations explicit and safe.

## Available Commands

The package provides four cleanup commands:

```bash
python manage.py cleanup_sessions
python manage.py cleanup_verification_codes
python manage.py cleanup_password_reset_codes
python manage.py cleanup_auth
```

The `cleanup_auth` command runs all three cleanup operations.

---

## 1. Cleanup Sessions

```bash
python manage.py cleanup_sessions
```

This command removes authentication sessions that are no longer useful.

A session is removed when either:

1. It has been explicitly revoked.
2. It has been inactive for longer than the configured inactivity period.

By default, the inactivity period is **30 days**.

### Example

```bash
python manage.py cleanup_sessions
```

Example output:

```text
Deleted 14 session record(s).
```

### Change the inactivity period

You can specify a different number of days:

```bash
python manage.py cleanup_sessions --inactive-days 90
```

This removes sessions that have not been used for 90 days, in addition to revoked sessions.

### Dry run

To see what would be deleted without actually deleting anything:

```bash
python manage.py cleanup_sessions --dry-run
```

Example:

```text
Revoked sessions: 5
Inactive sessions: 9
Dry run: 14 session(s) would be deleted.
```

This is recommended before running cleanup with a new inactivity period.

---

## 2. Cleanup Verification Codes

```bash
python manage.py cleanup_verification_codes
```

This command removes records from `VerificationCode`.

A verification record is removed when:

- It has already been used, or
- Both the numeric verification code and verification link have expired.

The command checks both expiration fields because a single verification record supports two verification methods:

```text
Numeric code
    ↓
code_expires_at

Email verification link
    ↓
link_expires_at
```

A record is only considered fully expired when both have expired.

### Example

```bash
python manage.py cleanup_verification_codes
```

Example output:

```text
Deleted 27 verification code record(s).
```

### Dry run

```bash
python manage.py cleanup_verification_codes --dry-run
```

Example:

```text
Dry run: 27 verification code(s) would be deleted.
```

---

## 3. Cleanup Password Reset Codes

```bash
python manage.py cleanup_password_reset_codes
```

This command performs the same type of cleanup for `PasswordResetCode`.

A password reset record is removed when:

- It has already been used, or
- Both the password reset code and reset link have expired.

### Example

```bash
python manage.py cleanup_password_reset_codes
```

Example output:

```text
Deleted 11 password reset code record(s).
```

### Dry run

```bash
python manage.py cleanup_password_reset_codes --dry-run
```

Example:

```text
Dry run: 11 password reset code(s) would be deleted.
```

---

# 4. Cleanup Everything

For most deployments, the easiest command to schedule is:

```bash
python manage.py cleanup_auth
```

This runs:

```text
cleanup_sessions
        ↓
cleanup_verification_codes
        ↓
cleanup_password_reset_codes
```

Example:

```bash
python manage.py cleanup_auth
```

Output:

```text
Cleaning authentication records...

Sessions
Deleted 14 session record(s).

Verification codes
Deleted 27 verification code record(s).

Password reset codes
Deleted 11 password reset code record(s).

Authentication cleanup complete.
```

---

## Dry Run

The combined command also supports `--dry-run`:

```bash
python manage.py cleanup_auth --dry-run
```

This performs the checks but does not delete anything.

Example:

```text
Cleaning authentication records...

Sessions
Revoked sessions: 5
Inactive sessions: 9
Dry run: 14 session(s) would be deleted.

Verification codes
Dry run: 27 verification code(s) would be deleted.

Password reset codes
Dry run: 11 password reset code(s) would be deleted.

Authentication cleanup complete.
```

---

## Session Inactivity Period

The default session inactivity period is:

```text
30 days
```

To change it:

```bash
python manage.py cleanup_auth --inactive-days 90
```

This means:

- Revoked sessions are always eligible for deletion.
- Active sessions are deleted only if they have not been used for the specified number of days.

For example:

```bash
python manage.py cleanup_auth --inactive-days 60
```

will remove:

```text
Revoked sessions
+
Sessions inactive for 60+ days
+
Used verification codes
+
Fully expired verification codes
+
Used password reset codes
+
Fully expired password reset codes
```

---

# Recommended Usage

During development, use the individual commands when testing cleanup behavior:

```bash
python manage.py cleanup_sessions --dry-run
python manage.py cleanup_verification_codes --dry-run
python manage.py cleanup_password_reset_codes --dry-run
```

Once the behavior has been verified, use:

```bash
python manage.py cleanup_auth
```

for regular maintenance.

---

# Scheduling Cleanup

Authentication cleanup should normally be run periodically rather than manually.

A daily or weekly schedule is sufficient for most applications.

For example:

```bash
python manage.py cleanup_auth
```

could be scheduled once per day.

The cleanup commands are safe to run repeatedly. Running them when there is nothing to delete simply results in zero records being removed.

For example:

```text
Deleted 0 session record(s).
Deleted 0 verification code record(s).
Deleted 0 password reset code record(s).
```

---

# Why Cleanup Is Necessary

Authentication records are intentionally stored in the database for a period of time.

For example, every verification request creates a `VerificationCode` record:

```text
Signup
   ↓
VerificationCode created
   ↓
Code sent to user
   ↓
User verifies
   ↓
Record marked as used
```

The record is no longer required after successful verification, but it remains in the database unless it is explicitly removed.

The same applies to:

- Revoked sessions
- Inactive sessions
- Expired verification codes
- Used verification codes
- Expired password reset codes
- Used password reset codes

Without periodic cleanup, these tables will continue to grow.

The cleanup commands provide a controlled way to remove these records without affecting active authentication data.

---

# Important Behavior

## Verification Codes

A verification record contains both:

```text
code_hash
token_hash
```

and both have their own expiration:

```text
code_expires_at
link_expires_at
```

The cleanup command does **not** delete the record simply because one of these has expired.

The record is considered fully expired only when:

```text
code_expires_at < current time
AND
link_expires_at < current time
```

This prevents the cleanup process from accidentally invalidating a still-valid verification method.

## Used Records

Records marked as:

```python
is_used = True
```

are always eligible for cleanup.

Once a verification or password reset has been successfully completed, keeping the record is generally unnecessary.

## Revoked Sessions

Sessions marked as:

```python
is_revoked = True
```

are eligible for immediate cleanup.

Revocation itself remains the mechanism used to invalidate the session. Cleanup simply removes the historical database record later.

---

# Recommended Production Command

For most installations, schedule:

```bash
python manage.py cleanup_auth
```

once per day.

If you want to retain inactive sessions for longer:

```bash
python manage.py cleanup_auth --inactive-days 90
```

A good production starting point is:

```text
Cleanup frequency: Daily
Session inactivity: 30–90 days
Verification cleanup: Every cleanup run
Password reset cleanup: Every cleanup run
```

The cleanup process should be treated as database maintenance, not as part of the authentication request flow. It should therefore run independently from login, signup, verification, and password-reset requests.
