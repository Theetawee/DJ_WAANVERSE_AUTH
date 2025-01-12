# API Routes Documentation

This document provides detailed information about the available API endpoints for authentication and user management.

## Authorization Endpoints

### Refresh Token

-   **URL:** `/refresh/`
-   **Method:** GET
-   **Description:** Refreshes the user's access token
-   **Name:** `dj_waanverse_auth_refresh_access_token`

### Current User

-   **URL:** `/me/`
-   **Method:** GET
-   **Description:** Retrieves the currently authenticated user's information
-   **Name:** `dj_waanverse_auth_authenticated_user`

### Logout

-   **URL:** `/logout/`
-   **Method:** POST
-   **Description:** Logs out the current user and invalidates their session
-   **Name:** `dj_waanverse_auth_logout`

### Home Page

-   **URL:** `/home/`
-   **Method:** GET
-   **Description:** Returns the home page for authenticated users
-   **Name:** `dj_waanverse_auth_home_page`

## Login Endpoints

### Login

-   **URL:** `/login/`
-   **Method:** POST
-   **Description:** Authenticates a user and creates a new session
-   **Name:** `dj_waanverse_auth_login`

## Signup Endpoints

### Signup

-   **URL:** `/signup/`
-   **Method:** POST
-   **Description:** Creates a new user account
-   **Name:** `dj_waanverse_auth_signup`

### Initiate Email Verification

-   **URL:** `/signup/email/initiate-verification/`
-   **Method:** POST
-   **Description:** Sends an email verification link to the user
-   **Name:** `dj_waanverse_auth_initiate_email_verification`

### Verify Email

-   **URL:** `/signup/email/verify/`
-   **Method:** POST
-   **Description:** Verifies the user's email address using the verification token
-   **Name:** `dj_waanverse_auth_verify_email`

## Multi-Factor Authentication (MFA) Endpoints

### Get MFA Secret

-   **URL:** `/mfa/get-secret/`
-   **Method:** GET
-   **Description:** Generates and returns an MFA secret for the user
-   **Name:** `dj_waanverse_auth_get_mfa_secret`

### Activate MFA

-   **URL:** `/mfa/activate/`
-   **Method:** POST
-   **Description:** Activates MFA for the user's account
-   **Name:** `dj_waanverse_auth_activate_mfa`

### Deactivate MFA

-   **URL:** `/mfa/deactivate/`
-   **Method:** POST
-   **Description:** Deactivates MFA for the user's account
-   **Name:** `dj_waanverse_auth_deactivate_mfa`

### MFA Login

-   **URL:** `/mfa/login/`
-   **Method:** POST
-   **Description:** Handles the MFA step of the login process
-   **Name:** `dj_waanverse_auth_mfa_login`

### Get Recovery Codes

-   **URL:** `/mfa/recovery-codes/`
-   **Method:** GET
-   **Description:** Retrieves the user's MFA recovery codes
-   **Name:** `dj_waanverse_auth_get_recovery_codes`

### Generate Recovery Codes

-   **URL:** `/mfa/generate-recovery-codes/`
-   **Method:** POST
-   **Description:** Generates new recovery codes for the user
-   **Name:** `dj_waanverse_auth_generate_recovery_codes`

## Password Management Endpoints

### Initiate Password Reset

-   **URL:** `/password/reset/`
-   **Method:** POST
-   **Description:** Initiates the password reset process by sending a reset link
-   **Name:** `dj_waanverse_auth_initiate_password_reset`

### Reset Password

-   **URL:** `/password/new-password/`
-   **Method:** POST
-   **Description:** Allows users to set a new password using a reset token
-   **Name:** `dj_waanverse_auth_reset_password`

## Base URL Structure

All endpoints are organized under the following structure:

-   Authentication endpoints are at the root level
-   Login-related endpoints are under `/login/`
-   MFA-related endpoints are under `/mfa/`
-   Signup-related endpoints are under `/signup/`
-   Password management endpoints are under `/password/`
