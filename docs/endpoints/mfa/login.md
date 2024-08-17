
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
