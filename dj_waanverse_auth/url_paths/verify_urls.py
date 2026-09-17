from django.urls import path
from dj_waanverse_auth.views.verify_views import (
    RequestVerificationView,
    VerifyAccountView,
)

urlpatterns = [
    path(
        "request/",
        RequestVerificationView.as_view(),
        name="dj_waanverse_auth_request_verification",
    ),
    path(
        "",
        VerifyAccountView.as_view(),
        name="dj_waanverse_auth_verify_account",
    ),
]
