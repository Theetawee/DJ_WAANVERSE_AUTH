from django.urls import path
from dj_waanverse_auth.views.login_views import authenticate_account
from dj_waanverse_auth.views.authorization_views import (
    authenticated_user,
    refresh_access_token,
    logout_view,
)


urlpatterns = [
    path("", authenticate_account, name="dj_waanverse_auth_auth"),
    path("me/", authenticated_user, name="dj_waanverse_auth_me"),
    path("refresh/", refresh_access_token, name="dj_waanverse_auth_refresh_token"),
    path("logout/<int:session_id>/", logout_view, name="dj_waanverse_auth_logout"),
]
