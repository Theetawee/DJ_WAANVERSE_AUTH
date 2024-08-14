from typing import TypedDict


class MessagesSchema(TypedDict):
    status_unverified: str
    status_verified: str
    email_sent: str
    email_required: str
    mfa_enabled_success: str
    mfa_already_activated: str
    mfa_invalid_otp: str
    mfa_not_activated: str
    mfa_deactivated: str
    mfa_login_failed: str
    mfa_login_success: str
    invalid_account: str
    no_account: str
    password_reset_code_sent: str
    password_reset_successful: str
    already_authenticated: str
    logout_successful: str
    mfa_required: str
    mfa_recovery_codes_generated: str
    mfa_setup_failed: str
    recovery_codes_regeneration_error: str
    token_error: str
    general_msg: str
    mfa_code_generated_email_subject: str
    email_exists: str
    passwords_mismatch: str
    username_exists: str
    password_validation_error: str
    invalid_email_code: str
    expired_email_code: str


class Messages(MessagesSchema):
    status_unverified = (
        "Your email is unverified. Please verify your email to continue."
    )
    status_verified = "Your email has been successfully verified."
    no_account = "No active account is found."
    email_sent = "A verification email has been sent to your email address."
    email_required = "A valid email address is required."
    mfa_enabled_success = "Multi-factor authentication has been successfully enabled."
    mfa_already_activated = "Multi-factor authentication is already activated."
    mfa_invalid_otp = "The OTP provided is invalid. Please try again."
    mfa_not_activated = "Multi-factor authentication is not activated for this account."
    mfa_deactivated = "Multi-factor authentication has been deactivated."
    mfa_login_failed = "MFA login failed. Invalid OTP or recovery code."
    mfa_login_success = "MFA login successful."
    invalid_account = "The account provided is invalid. Please try again."
    password_reset_code_sent = (
        "A password reset code has been sent to your email address."
    )
    password_reset_successful = "Your password has been successfully reset."
    already_authenticated = "You are already authenticated."
    logout_successful = "You have been successfully logged out."
    mfa_required = "Multi-factor authentication is required for this action."
    mfa_recovery_codes_generated = (
        "New MFA recovery codes have been successfully generated."
    )
    mfa_setup_failed = "An error occurred while setting up multi-factor authentication."
    recovery_codes_regeneration_error = (
        "An error occurred while generating recovery codes. Please try again."
    )
    token_error = "An error occurred while processing the token. Please try again."
    general_msg = "An error occurred. Please try again."
    mfa_code_generated_email_subject = "New MFA Recovery Codes Generated"
    username_exists = "Username already exists."
    passwords_mismatch = "Passwords do not match."
    email_exists = "Email already exists."
    password_validation_error = "password must contain at least one digit, one uppercase letter, one lowercase letter, one special character (e.g., @, #, $, etc.)"
    invalid_email_code = "Invalid code."
    expired_email_code = "Code expired."
