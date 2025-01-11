from django.urls import path

from dj_waanverse_auth.views.login_views import mfa_login_view
from dj_waanverse_auth.views.mfa_views import (
    activate_mfa_view,
    deactivate_mfa_view,
    generate_recovery_codes_view,
    get_mfa_secret_view,
    get_recovery_codes_view,
)

urlpatterns = [
    path("get-secret/", get_mfa_secret_view, name="dj_waanverse_auth_get_mfa_secret"),
    path("deactivate/", deactivate_mfa_view, name="dj_waanverse_auth_deactivate_mfa"),
    path("login/", mfa_login_view, name="dj_waanverse_auth_mfa_login"),
    path(
        "activate/",
        activate_mfa_view,
        name="dj_waanverse_auth_activate_mfa",
    ),
    path(
        "recovery-codes/",
        get_recovery_codes_view,
        name="dj_waanverse_auth_get_recovery_codes",
    ),
    path(
        "generate-recovery-codes/",
        generate_recovery_codes_view,
        name="dj_waanverse_auth_generate_recovery_codes",
    ),
]
