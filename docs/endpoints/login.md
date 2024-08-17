# Login Endpoint

-   **Route:** `/login`
-   **Description:** Authenticates a user and returns appropriate responses based on the account state.

!!! note "Note"
    The response varies depending on the account status: - **MFA Enabled:** Returns a `mfa` key with the user ID. - **Email Not Verified:** Returns an `email` key with the user's email and a `msg` key with a message prompting email verification and a verification email is sent to the user's email address. - **Email Verified, MFA Not Enabled:** Returns `access_token` and `refresh_token` keys along with user details in the `user` key.

-   **Method:** `POST`

## Request Body

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

## Successful Responses

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

## Bad Responses

-   **Status Code:** `401 Unauthorized`
-   **Content:**
    ```json
    {
        "detail": "Incorrect authentication credentials.",
        "code": "authentication_failed",
        "msg": "[Messages.no_account]*"
    }
    ```

## Explanation of Responses

1. **MFA Enabled:** If multi-factor authentication (MFA) is enabled, the response will include the user ID in the `mfa` key. The MFA cookie, containing the user ID, is automatically set in the response headers.

2. **Email Not Verified:** If the user's email is not verified, the response includes the user's email in the `email` key and a message prompting email verification in the `msg` key. A verification email containing the code is automatically sent to the user's email address.

3. **Email Verified, MFA Not Enabled:** If the email is verified and MFA is not enabled, the response includes access and refresh tokens in the respective keys, along with user details in the `user` key as defined by the `USER_CLAIM_SERIALIZER`. Authentication cookies are automatically set in the response headers.

4. **Cookies:** Authentication cookies, such as those for session management and MFA, are automatically set in the response headers and do not appear in the response body. These cookies are used for authorization in web applications.

5. **Authorization:**
    - **Web Applications:** Authorization is managed through cookies, which are automatically set and read by the browser.
    - **Mobile Applications:** Authorization is handled via the `Authorization` Bearer header, where the access token must be included. The refresh token should be securely stored by the client to refresh the access token when necessary.
