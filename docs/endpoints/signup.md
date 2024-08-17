
## Signup

-   **Route:** `POST /signup`
-   **Description:** Registers a new user account.
-   **Method:** `POST`
-   **Successful Response:**
    -   **Status Code:** `201 Created`
    -   **Content:**
        ```json
        {
            "id": "integer",
            "username": "string",
            "email": "string"
        }
        ```
-   **Bad Response:**
    -   **Status Code:** `400 Bad Request`
    -   **Content:**
        ```json
        {
            "detail": "User already exists or invalid data"
        }
        ```
