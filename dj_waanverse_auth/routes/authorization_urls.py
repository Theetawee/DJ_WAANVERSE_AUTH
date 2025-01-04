from django.urls import path

from dj_waanverse_auth.views.authorization_views import (
    authenticated_user,
    logout_view,
    refresh_access_token,
)

urlpatterns = [
    path("refresh/", refresh_access_token, name="refresh_access_token"),
    path("me/", authenticated_user, name="authenticated_user"),
    path("logout/", logout_view, name="logout"),
]
