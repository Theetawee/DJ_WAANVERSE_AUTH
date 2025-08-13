from django.urls import path

from dj_waanverse_auth.views.login_views import (
    login_view,
    get_login_code,
    generate_registration_options_view,
    verify_registration_view,
)

urlpatterns = [
    path("", login_view, name="dj_waanverse_auth_login"),
    path("code/", get_login_code, name="dj_waanverse_auth_get_login_code"),
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
]
