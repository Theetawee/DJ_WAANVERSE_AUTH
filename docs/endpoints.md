# API Endpoints

## Login

-   **Route:** `/login`
-   **Description:** Authenticates a user and returns appropriate responses based on the account state.

!!! note "Note"
The response varies depending on the account status: - **MFA Enabled:** Returns a `mfa` key with the user ID. - **Email Not Verified:** Returns an `email` key with the user's email and a `msg` key with a message prompting email verification and a verification email is sent to the user's email address. - **Email Verified, MFA Not Enabled:** Returns `access_token` and `refresh_token` keys along with user details in the `user` key.

-   **Method:** `POST`

### Request Body

-   **Content-Type:** `application/json`
-   **Body:**
    ```json
    {
        "login_field": "string",
        "password": "string"
    }
    ```
-   **Fields:**
    -   `login_field` (string): The login field (one of those specified in `AUTHENTICATION_METHODS`) of the user attempting to log in.
    -   `password` (string): The password associated with the `login_field`.

### Successful Responses

-   **Status Code:** `200 OK`
-   **Content (MFA Enabled):**
    ```json
    {
        "mfa": "user_id"
    }
    ```
-   **Content (Email Not Verified):**
    ```json
    {
        "email": "user@example.com",
        "msg": "[Messages.status_unverified]*"
    }
    ```
-   **Content (Email Verified, MFA Not Enabled):**
    ```json
    {
        "access_token": "string",
        "refresh_token": "string",
        "user": {
            "id": "integer",
            "username": "string"
        }
    }
    ```

### Bad Responses

-   **Status Code:** `401 Unauthorized`
-   **Content:**
    ```json
    {
        "detail": "Incorrect authentication credentials.",
        "code": "authentication_failed",
        "msg": "[Messages.no_account]*"
    }
    ```

### Explanation of Responses

1. **MFA Enabled:** If multi-factor authentication (MFA) is enabled for the account, the response includes the user ID in the `mfa` key.
2. **Email Not Verified:** If the user's email is not verified, the response includes the user's email in the `email` key and a message prompting email verification in the `msg` key and a verification email containing the code is sent to the user's email address.
3. **Email Verified, MFA Not Enabled:** If the email is verified and MFA is not enabled, the response includes access and refresh tokens, along with user details in the `user` key.

Cookies related to authentication are automatically set in the response headers and are not included in the response body.




## Refresh Token

- **Route:** `/token/refresh`
- **Description:** Refreshes the access token using the refresh token provided in the request body or via cookies.

- **Method:** `POST`

### Request Body

- **Content-Type:** `application/json` (if using a request body)
- **Body:**
    ```json
    {
        "refresh_token": "string"
    }
    ```
- **Fields:**
  - `refresh_token` (string): The refresh token used to obtain a new access token. This is required for applications but optional for websites where the token is handled via cookies.

### Successful Response

- **Status Code:** `200 OK`
- **Content:**
    ```json
    {
        "access": "string"
    }
    ```
- **Explanation:** Returns a new access token.

### Bad Responses

- **Status Code:** `401 Unauthorized`
- **Content:**
    ```json
    {
        "detail": "Invalid or expired refresh token"
    }
    ```
- **Explanation:** Indicates that the provided refresh token is invalid or has expired.

### Notes

- For web applications, the refresh token is managed via cookies and does not need to be included in the request body.
- For mobile or other applications, include the refresh token in the request body to obtain a new access token.




## Resend Verification Email

-   **Route:** `POST /resend/email`
-   **Description:** Resends the verification email to the user.
-   **Method:** `POST`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
            "detail": "Verification email sent"
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `400 Bad Request`
    -   **Content:**
        ```json
        {
            "detail": "Email address not found"
        }
        ```

## Verify Email

-   **Route:** `POST /verify/email`
-   **Description:** Verifies the user's email address using the provided verification code.
-   **Method:** `POST`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
            "detail": "Email verified"
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `400 Bad Request`
    -   **Content:**
        ```json
        {
            "detail": "Invalid verification code"
        }
        ```

## Signup

-   **Route:** `POST /signup`
-   **Description:** Registers a new user account.
-   **Method:** `POST`
-   **Successful Response:**
    -   **Status Code:** `201 Created`
    -   **Content:**
        ```json
        {
            "id": "integer",
            "username": "string",
            "email": "string"
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `400 Bad Request`
    -   **Content:**
        ```json
        {
            "detail": "User already exists or invalid data"
        }
        ```

## User Info

-   **Route:** `GET /me`
-   **Description:** Retrieves information about the currently authenticated user.
-   **Method:** `GET`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
            "id": "integer",
            "username": "string",
            "email": "string"
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `401 Unauthorized`
    -   **Content:**
        ```json
        {
            "detail": "Authentication credentials were not provided"
        }
        ```

## Enable MFA

-   **Route:** `POST /mfa/activate`
-   **Description:** Activates multi-factor authentication (MFA) for the user.
-   **Method:** `POST`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
            "detail": "MFA activated"
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `400 Bad Request`
    -   **Content:**
        ```json
        {
            "detail": "MFA activation failed"
        }
        ```

## Verify MFA

-   **Route:** `POST /mfa/verify`
-   **Description:** Verifies the MFA code provided by the user.
-   **Method:** `POST`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
            "detail": "MFA verified"
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `400 Bad Request`
    -   **Content:**
        ```json
        {
            "detail": "Invalid MFA code"
        }
        ```

## MFA Status

-   **Route:** `GET /mfa/status`
-   **Description:** Checks the current status of MFA for the user.
-   **Method:** `GET`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
            "mfa_enabled": true
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `401 Unauthorized`
    -   **Content:**
        ```json
        {
            "detail": "Authentication credentials were not provided"
        }
        ```

## Regenerate Recovery Codes

-   **Route:** `POST /mfa/regenerate-codes`
-   **Description:** Generates new MFA recovery codes for the user.
-   **Method:** `POST`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
          "recovery_codes": ["string", "string", ...]
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `400 Bad Request`
    -   **Content:**
        ```json
        {
            "detail": "Failed to regenerate recovery codes"
        }
        ```

## Deactivate MFA

-   **Route:** `POST /mfa/deactivate`
-   **Description:** Deactivates MFA for the user.
-   **Method:** `POST`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
            "detail": "MFA deactivated"
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `400 Bad Request`
    -   **Content:**
        ```json
        {
            "detail": "MFA deactivation failed"
        }
        ```

## Logout

-   **Route:** `POST /logout`
-   **Description:** Logs out the user and invalidates the session.
-   **Method:** `POST`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
            "detail": "Logged out successfully"
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `401 Unauthorized`
    -   **Content:**
        ```json
        {
            "detail": "Invalid or expired token"
        }
        ```

## MFA Login

-   **Route:** `POST /mfa/login`
-   **Description:** Logs in a user using MFA.
-   **Method:** `POST`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
            "access": "string",
            "refresh": "string"
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `401 Unauthorized`
    -   **Content:**
        ```json
        {
            "detail": "Invalid MFA code or credentials"
        }
        ```

## Reset Password

-   **Route:** `POST /password/reset`
-   **Description:** Initiates the password reset process for the user.
-   **Method:** `POST`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
            "detail": "Password reset email sent"
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `400 Bad Request`
    -   **Content:**
        ```json
        {
            "detail": "Invalid email address or user not found"
        }
        ```

## Verify Reset Password

-   **Route:** `POST /password/reset/new`
-   **Description:** Verifies the password reset code and sets a new password.
-   **Method:** `POST`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
            "detail": "Password reset successful"
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `400 Bad Request`
    -   **Content:**
        ```json
        {
            "detail": "Invalid reset code or password"
        }
        ```

Feel free to adjust the responses and descriptions according to the actual behavior of your API endpoints.
