from dj_waanverse_auth.views.logout_views import LogoutView

from django.urls import path

url_patterns = [path("", LogoutView.as_view(), name="dj_waanverse_auth_logout")]
