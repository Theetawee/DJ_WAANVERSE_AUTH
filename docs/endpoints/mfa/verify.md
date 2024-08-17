
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
