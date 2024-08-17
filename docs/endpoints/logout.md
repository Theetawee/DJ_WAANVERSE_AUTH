
## Logout

-   **Route:** `POST /logout`
-   **Description:** Logs out the user and invalidates the session.
-   **Method:** `POST`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
            "detail": "Logged out successfully"
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `401 Unauthorized`
    -   **Content:**
        ```json
        {
            "detail": "Invalid or expired token"
        }
        ```
