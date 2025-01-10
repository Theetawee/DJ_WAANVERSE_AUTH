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
        name="email_initiate",
    ),
    path("email/verify/", verify_email, name="email_verify"),
    path("", signup_view, name="dj_waanverse_auth_signup"),
]
