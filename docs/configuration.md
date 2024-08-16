# Configuration
`dj_waanverse_auth` comes with a number of default settings. These can be overridden in your `settings.py` file using the `WAANVERSE_AUTH` dictionary as shown below.

## Example

```python
WAANVERSE_AUTH = {
    ...
    "USER_CLAIM_SERIALIZER": "dj_waanverse_auth.serializers.BasicAccountSerializer",
    ...
}
```

## Available Settings

The `dj_waanverse_auth` package provides a flexible configuration system to tailor the authentication process to your application's needs. Below is a list of available settings, along with their descriptions:

### AUTH_METHODS
- **Type:** `List[str]`
- **Default:** `["username"]`
- **Description:** Defines the methods of authentication allowed. Allowed values are `username`, `email` and `phone_number`.

!!! warning "Important"

    Each value specified in the configuration must correspond to an existing field in the accounts model. For instance, if `AUTH_METHODS` includes `["username", "email", "phone_number"]`, the accounts model must contain fields for `username`, `email`, and `phone_number`. Failure to do so will result in errors during authentication.


### MFA_RECOVERY_CODES_COUNT
- **Type:** `int`
- **Default:** `10`
- **Description:** The number of multi-factor authentication (MFA) recovery codes generated for a user. These codes are used to regain access in case the primary MFA method is unavailable.

### ACCESS_TOKEN_COOKIE
- **Type:** `str`
- **Default:** `"access_token"`
- **Description:** The name of the cookie used to store the JWT access token.

### REFRESH_TOKEN_COOKIE
- **Type:** `str`
- **Default:** `"refresh_token"`
- **Description:** The name of the cookie used to store the JWT refresh token.

### COOKIE_PATH
- **Type:** `str`
- **Default:** `"/"`
- **Description:** Specifies the path for which the cookies are valid. It can be set to a specific path if necessary.

### COOKIE_DOMAIN
- **Type:** `Optional[str]`
- **Default:** `None`
- **Description:** Specifies the domain for which the cookies are valid. If not set, the cookies are valid for the domain that issued the cookie.

### COOKIE_SAMESITE_POLICY
- **Type:** `str`
- **Default:** `"Lax"`
- **Description:** Defines the SameSite attribute of the cookie, which controls whether cookies are sent along with cross-site requests. The options are `"Lax"`, `"Strict"`, or `"None"`.

### COOKIE_SECURE_FLAG
- **Type:** `bool`
- **Default:** `False`
- **Description:** If set to `True`, the cookie will only be sent over HTTPS connections.

### COOKIE_HTTP_ONLY_FLAG
- **Type:** `bool`
- **Default:** `True`
- **Description:** If set to `True`, the cookie will not be accessible via JavaScript, providing additional security.

### MFA_COOKIE_NAME
- **Type:** `str`
- **Default:** `"mfa_token"`
- **Description:** The name of the cookie used to store the MFA token.

### MFA_COOKIE_DURATION
- **Type:** `timedelta`
- **Default:** `timedelta(minutes=2)`
- **Description:** The duration for which the MFA cookie remains valid.

!!! warning "Important"

    The `MFA_COOKIE_DURATION` defines the time window a user has to submit their Multi-Factor Authentication (MFA) token. If this duration elapses, the user will need to log in again to proceed.



### USER_CLAIM_SERIALIZER_CLASS
- **Type:** `str`
- **Default:** `"dj_waanverse_auth.serializers.BasicAccountSerializer"`
- **Description:** Specifies the serializer class used for user claims in the JWT payload and response.

### REGISTRATION_SERIALIZER_CLASS
- **Type:** `str`
- **Default:** `"dj_waanverse_auth.serializers.SignupSerializer"`
- **Description:** Specifies the serializer class used for user registration.

### USERNAME_MIN_LENGTH
- **Type:** `int`
- **Default:** `4`
- **Description:** The minimum length required for usernames.

### DISALLOWED_USERNAMES
- **Type:** `List[str]`
- **Default:** `["waanverse"]`
- **Description:** A list of usernames that are not allowed during registration.

### USER_DETAIL_SERIALIZER_CLASS
- **Type:** `str`
- **Default:** `"dj_waanverse_auth.serializers.AccountSerializer"`
- **Description:** Specifies the serializer class used for user detail views.

### ENABLE_EMAIL_ON_LOGIN
- **Type:** `bool`
- **Default:** `True`
- **Description:** If set to `True`, users will receive an email when them or someone else logs into their account.


### CONFIRMATION_CODE_DIGITS
- **Type:** `int`
- **Default:** `6`
- **Description:** The number of digits in the email confirmation code.

### PLATFORM_NAME
- **Type:** `str`
- **Default:** `"Waanverse Auth"`
- **Description:** The name of the platform, used in email templates and other messaging contexts.

### EMAIL_VERIFICATION_CODE_DURATION
- **Type:** `timedelta`
- **Default:** `timedelta(minutes=10)`
- **Description:** The duration for which the email verification code remains valid.

### MFA_ISSUER_NAME
- **Type:** `str`
- **Default:** `"Waanverse Labs Inc."`
- **Description:** The name of the issuer displayed in MFA applications like Google Authenticator.


### MFA_CODE_DIGITS
- **Type:** `int`
- **Default:** `6`
- **Description:** The number of digits in the MFA code.

### MFA_EMAIL_ALERTS_ENABLED
- **Type:** `bool`
- **Default:** `True`
- **Description:** If set to `True`, users will receive email alerts for MFA-related activities like generation of recovery codes.

### PASSWORD_RESET_CODE_DURATION
- **Type:** `timedelta`
- **Default:** `timedelta(minutes=10)`
- **Description:** The duration for which the password reset code remains valid.

### PASSWORD_RESET_COOLDOWN_PERIOD
- **Type:** `timedelta`
- **Default:** `timedelta(minutes=5)`
- **Description:** The cooldown period after a password reset attempt, during which another attempt cannot be made.

### PASSWORD_RESET_MAX_ATTEMPTS
- **Type:** `int`
- **Default:** `1`
- **Description:** The maximum number of password reset attempts allowed before the system temporarily locks further attempts till the cooldown period.

