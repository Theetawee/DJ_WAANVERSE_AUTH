from django.urls import path

from dj_waanverse_auth.views.authorization_views import (
    authenticated_user,
    get_device_info,
    get_user_sessions,
    grant_access_view,
    logout_view,
    refresh_access_token,
    update_account,
)

urlpatterns = [
    path(
        "refresh/", refresh_access_token, name="dj_waanverse_auth_refresh_access_token"
    ),
    path("me/", authenticated_user, name="dj_waanverse_auth_authenticated_user"),
    path("logout/", logout_view, name="dj_waanverse_auth_logout"),
    path("sessions/", get_user_sessions, name="dj_waanverse_auth_get_user_sessions"),
    path(
        "grant-access/",
        grant_access_view,
        name="dj_waanverse_auth_grant_access",
    ),
    path("device-info/", get_device_info, name="dj_waanverse_auth_get_device_info"),
    path("update-account/", update_account, name="dj_waanverse_auth_update_account"),
]
