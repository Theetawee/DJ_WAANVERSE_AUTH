
# Refresh Token Endpoint

-   **Route:** `/token/refresh`
-   **Description:** Refreshes the access token using the refresh token provided in the request body or via cookies.

-   **Method:** `POST`

## Request Body

-   **Content-Type:** `application/json` (if using a request body)
-   **Body:**
    ```json
    {
        "refresh_token": "string"
    }
    ```
-   **Fields:**
    -   `refresh_token` (string): The refresh token used to obtain a new access token. This is required for applications but optional for websites where the token is handled via cookies.

## Successful Response

-   **Status Code:** `200 OK`
-   **Content:**
    ```json
    {
        "access_token": "string"
    }
    ```
-   **Explanation:** Returns a new access token and automatically sets it in the response cookies.

## Bad Responses

-   **Status Code:** `401 Unauthorized`
-   **Content:**
    ```json
    {
        "msg": "[Messages.token_error]*"
    }
    ```
-   **Explanation:** Indicates that the provided refresh token is invalid or has expired.

## Notes

-   For web applications, the refresh token is managed via cookies and does not need to be included in the request body.
-   For mobile or other applications, include the refresh token in the request body to obtain a new access token.


