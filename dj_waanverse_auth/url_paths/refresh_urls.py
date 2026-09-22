from dj_waanverse_auth.views.refresh_views import RefreshView
from django.urls import path

url_patterns = [path("", RefreshView.as_view(), name="dj_waanverse_auth_refresh")]
