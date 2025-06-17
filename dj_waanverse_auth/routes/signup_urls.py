from django.urls import path

from dj_waanverse_auth.views.signup_views import (
    activate_email_address,
    activate_phone_number,
    send_email_verification_code,
    send_phone_number_verification_code_view,
    signup_view,
)

urlpatterns = [
    path(
        "email/send-code/",
        send_email_verification_code,
        name="dj_waanverse_auth_send_email_verification_code",
    ),
    path("", signup_view, name="dj_waanverse_auth_signup"),
    path(
        "email/activate/",
        activate_email_address,
        name="dj_waanverse_auth_activate_email",
    ),
    path(
        "phone/send-code/",
        send_phone_number_verification_code_view,
        name="dj_waanverse_auth_send_phone_number_verification_code",
    ),
    path(
        "phone/activate/",
        activate_phone_number,
        name="dj_waanverse_auth_activate_phone",
    ),
]
