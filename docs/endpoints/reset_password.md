
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
