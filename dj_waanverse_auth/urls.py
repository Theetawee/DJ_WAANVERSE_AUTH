from django.urls import path
from .views import (
    refresh_token_view,
    login_view,
    reverify_email,
    verify_email,
    signup_view,
    user_info,
    enable_mfa,
    verify_mfa,
    mfa_status,
    regenerate_recovery_codes,
    logout_view,
    mfa_login,
    reset_password,
    verify_reset_password,
    DeactivateMfaView,
)

urlpatterns = [
    path("login", login_view, name="login"),
    path("token/refresh", refresh_token_view, name="refresh_token"),
    path("reverify_email", reverify_email, name="reverify_email"),
    path("verify/email", verify_email, name="verify_email"),
    path("signup", signup_view, name="signup"),
    path("me", user_info, name="user_info"),
    path("mfa/activate", enable_mfa, name="enable_mfa"),
    path("mfa/verify", verify_mfa, name="verify_mfa"),
    path("mfa/status", mfa_status, name="mfa_activated"),
    path("mfa/regenerate-codes", regenerate_recovery_codes, name="regenerate_codes"),
    path("mfa/deactivate", DeactivateMfaView.as_view(), name="deactivate_mfa"),
    path("logout", logout_view, name="logout"),
    path("mfa/login", mfa_login, name="verify_mfa_auth"),
    path("password/reset", reset_password, name="reset_password"),
    path("reset/verify", verify_reset_password, name="verify_reset_password"),
]
