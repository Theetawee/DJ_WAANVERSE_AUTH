from django.urls import path

from dj_waanverse_auth.views.authorization_views import refresh_access_token

urlpatterns = [
    path("refresh/", refresh_access_token, name="refresh_access_token"),
]
