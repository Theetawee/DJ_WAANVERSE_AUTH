from typing import TypedDict

from django.utils.translation import gettext_lazy as _

from .settings import auth_config


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
    email_already_verified: str
    no_credentials: str
    user_creation_error: str
    password_reset_attempts_limit: str
    invalid_password: str
    invalid_code: str
    expired_code: str
    email_exists: str
    password_mismatch: str
    password_validation_error: str
    username_exists: str
    email_not_found: str

    # Email subjects
    verify_email_subject: str
    login_email_subject: str
    mfa_deactivated_email_subject: str
    reset_password_email_subject: str
    mfa_code_generated_email_subject: str
    password_reset_complete_email_subject: str


class Messages(MessagesSchema):
    status_unverified = _(
        "Your email is still unverified. Please verify your email to continue."
    )
    status_verified = _(
        "Your email has been successfully verified. You can now proceed."
    )
    no_account = _("No active account found with the provided details.")
    email_sent = _("A verification email has been sent to your inbox.")
    email_required = _("A valid email address is required to continue.")
    mfa_enabled_success = _(
        "Multi-factor authentication has been successfully activated for your account."
    )
    mfa_already_activated = _(
        "Your account already has multi-factor authentication enabled."
    )
    mfa_invalid_otp = _(
        "The One-Time Password (OTP) you entered is invalid. Please try again."
    )
    mfa_not_activated = _(
        "Multi-factor authentication is not enabled for this account."
    )
    mfa_deactivated = _(
        "Multi-factor authentication has been successfully deactivated."
    )
    mfa_login_failed = _(
        "MFA login failed. Please check the OTP or recovery code you entered."
    )
    mfa_login_success = _("MFA login was successful. You are now logged in.")
    invalid_account = _(
        "The provided account information is invalid. Please check and try again."
    )
    password_reset_code_sent = _(
        "A password reset code has been sent to your email address, if an account exists."
    )
    password_reset_successful = _("Your password has been successfully reset.")
    already_authenticated = _("You are already logged in.")
    logout_successful = _("You have successfully logged out of your account.")
    mfa_required = _(
        "Multi-factor authentication is required to proceed with this action."
    )
    mfa_recovery_codes_generated = _(
        "New multi-factor authentication recovery codes have been successfully generated."
    )
    mfa_setup_failed = _(
        "An error occurred during the setup of multi-factor authentication. Please try again."
    )
    recovery_codes_regeneration_error = _(
        "An error occurred while regenerating MFA recovery codes. Please try again."
    )
    token_error = _("An error occurred while processing the token. Please try again.")
    general_msg = _("An error occurred. Please try again later.")
    mfa_code_generated_email_subject = _("New MFA Recovery Codes Generated")
    email_already_verified = _("Your email address has already been verified.")
    no_credentials = _(
        "No valid credentials were provided. Please check your input and try again."
    )
    user_creation_error = _(
        "An error occurred while creating the user account. Please try again."
    )
    password_reset_attempts_limit = _(
        f"Too many attempts. Please wait {auth_config.password_reset_cooldown} minutes before trying again."
    )
    invalid_password = _("The password you provided is incorrect. Please try again.")
    mfa_deactivated_email_subject = _(
        "Multi-factor Authentication Deactivation Confirmation"
    )
    reset_password_email_subject = _("Password Reset Request")
    invalid_code = _("The code you entered is invalid. Please check and try again.")
    email_exists = _("An account with this email address already exists.")
    password_mismatch = _(
        "The passwords you entered do not match. Please check and try again."
    )
    verify_email_subject = _("Please verify your email address")
    login_email_subject = _("New Login Alert")
    expired_code = _("The code you provided has expired. Please request a new one.")
    username_exists = _("An account with this username already exists.")

    email_not_found = _(
        "No account was found associated with the provided email address."
    )
    password_reset_complete_email_subject = _("Password Reset Successful")
