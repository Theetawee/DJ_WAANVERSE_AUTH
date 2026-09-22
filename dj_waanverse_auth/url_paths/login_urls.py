from dj_waanverse_auth.views.login_views import LoginView

from django.urls import path

url_patterns = [path("", LoginView.as_view(), name="dj_waanverse_auth_login")]
