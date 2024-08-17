
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
