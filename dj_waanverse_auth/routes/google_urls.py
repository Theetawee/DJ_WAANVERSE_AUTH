from django.urls import path

from dj_waanverse_auth.views.google_auth_views import google_callback, google_login

urlpatterns = [
    path("login/", google_login, name="dj_waanverse_auth_google_login"),
    path("callback/", google_callback, name="dj_waanverse_auth_google_callback"),
]
