from django.urls import path
from dj_waanverse_auth.views.password_reset_views import (
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

url_patterns = [
    path(
        "request/",
        PasswordResetRequestView.as_view(),
        name="dj_waanverse_auth_password_reset_request",
    ),
    path(
        "confirm/",
        PasswordResetConfirmView.as_view(),
        name="dj_waanverse_auth_password_reset_confirm",
    ),
]
