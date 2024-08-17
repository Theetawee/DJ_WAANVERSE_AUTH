
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
