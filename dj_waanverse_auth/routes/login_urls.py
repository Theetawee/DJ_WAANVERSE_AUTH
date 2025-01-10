from django.urls import path

from dj_waanverse_auth.views.login_views import login_view

urlpatterns = [
    path("", login_view, name="dj_waanverse_auth_login"),
]
