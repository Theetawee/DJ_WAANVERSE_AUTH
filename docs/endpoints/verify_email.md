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
