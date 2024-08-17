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
