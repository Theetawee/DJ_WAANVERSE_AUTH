from django.urls import path

from dj_waanverse_auth.views.signup_views import (
    initiate_email_verification,
    signup_view,
    verify_email,
)

urlpatterns = [
    path(
        "email/initiate-verification/",
        initiate_email_verification,
        name="dj_waanverse_auth_initiate_email_verification",
    ),
    path("email/verify/", verify_email, name="dj_waanverse_auth_verify_email"),
    path("", signup_view, name="dj_waanverse_auth_signup"),
]
