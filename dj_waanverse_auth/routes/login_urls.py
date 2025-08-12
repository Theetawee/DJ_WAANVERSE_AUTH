from django.urls import path

from dj_waanverse_auth.views.login_views import login_view, get_login_code

urlpatterns = [
    path("", login_view, name="dj_waanverse_auth_login"),
    path("code/", get_login_code, name="dj_waanverse_auth_get_login_code"),
]
