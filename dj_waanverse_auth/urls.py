from django.urls import path
from dj_waanverse_auth.views.login_views import authenticate_account
from dj_waanverse_auth.views.authorization_views import authenticated_user


urlpatterns = [
    path("", authenticate_account, name="dj_waanverse_auth_auth"),
    path("me/", authenticated_user, name="dj_waanverse_auth_me"),
]
