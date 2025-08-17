from django.urls import path

from dj_waanverse_auth.views.login_views import (
    login_view,
    generate_registration_options_view,
    verify_registration_view,
    generate_authentication_options_view,
    verify_authentication_view,
)

urlpatterns = [
    path("", login_view, name="dj_waanverse_auth_login"),
    path(
        "webauthn/options/",
        generate_registration_options_view,
        name="dj_waanverse_auth_generate_registration_options",
    ),
    path(
        "webauthn/verify/",
        verify_registration_view,
        name="dj_waanverse_auth_verify_registration",
    ),
    path(
        "webauthn/",
        generate_authentication_options_view,
        name="dj_waanverse_auth_generate_authentication_options",
    ),
    path(
        "webauthn/verify-challenge/",
        verify_authentication_view,
        name="dj_waanverse_auth_verify_authentication",
    ),
]
