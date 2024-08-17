
## User Info

-   **Route:** `GET /me`
-   **Description:** Retrieves information about the currently authenticated user.
-   **Method:** `GET`
-   **Successful Response:**
    -   **Status Code:** `200 OK`
    -   **Content:**
        ```json
        {
            "id": "integer",
            "username": "string",
            "email": "string"
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
