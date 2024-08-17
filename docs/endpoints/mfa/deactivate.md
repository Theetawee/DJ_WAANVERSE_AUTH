
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
