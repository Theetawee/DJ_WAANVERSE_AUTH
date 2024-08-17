
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

