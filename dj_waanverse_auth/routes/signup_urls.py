from django.urls import path

from dj_waanverse_auth.views.signup_views import (
    send_email_verification_link,
    signup_view,
)

urlpatterns = [
    path(
        "email/add/",
        send_email_verification_link,
        name="dj_waanverse_auth_add_email",
    ),
    path("", signup_view, name="dj_waanverse_auth_signup"),
]
