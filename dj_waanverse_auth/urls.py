from django.urls import path
from dj_waanverse_auth.views.login_views import login_view
from dj_waanverse_auth.views.authorization_views import (
    authenticated_user,
    refresh_access_token,
    logout_view,
)
from dj_waanverse_auth.views.passkey_views import (
    register_begin,
    register_complete,
    login_begin,
    login_complete,
)
from dj_waanverse_auth.views.signup_views import signup_view

urlpatterns = [
    path("signup/", signup_view, name="dj_waanverse_auth_signup"),
    path("me/", authenticated_user, name="dj_waanverse_auth_me"),
    path("refresh/", refresh_access_token, name="dj_waanverse_auth_refresh_token"),
    path("logout/<int:session_id>/", logout_view, name="dj_waanverse_auth_logout"),
    path("login/", login_view, name="dj_waanverse_auth_login"),
    # Passkey
    path(
        "passkey/register/",
        register_begin,
        name="dj_waanverse_auth_passkey_register",
    ),
    path(
        "passkey/register/complete/",
        register_complete,
        name="dj_waanverse_auth_passkey_register_complete",
    ),
    path(
        "passkey/login/",
        login_begin,
        name="dj_waanverse_auth_passkey_login",
    ),
    path(
        "passkey/login/complete/",
        login_complete,
        name="dj_waanverse_auth_passkey_login_complete",
    ),
]
