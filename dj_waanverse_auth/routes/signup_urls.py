from django.urls import path

from dj_waanverse_auth.views.signup_views import (
    activate_email_address,
    add_email_view,
    signup_view,
)

urlpatterns = [
    path(
        "email/add/",
        add_email_view,
        name="dj_waanverse_auth_add_email",
    ),
    path("", signup_view, name="dj_waanverse_auth_signup"),
    path(
        "email/activate/",
        activate_email_address,
        name="dj_waanverse_auth_activate_email",
    ),
]
