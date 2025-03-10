from django.urls import path

from dj_waanverse_auth.views.signup_views import (
    activate_email_address,
    activate_phone_number,
    add_email_view,
    add_phone_number_view,
    signup_view,
    update_account_status,
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
    path("phone/add/", add_phone_number_view, name="dj_waanverse_auth_add_phone"),
    path(
        "phone/activate/",
        activate_phone_number,
        name="dj_waanverse_auth_activate_phone",
    ),
    path(
        "update-account-status/",
        update_account_status,
        name="dj_waanverse_auth_update_account_status",
    ),
]
