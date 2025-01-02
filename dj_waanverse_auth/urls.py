from django.urls import include, path

from dj_waanverse_auth.routes import login_urls

urlpatterns = [
    path("login/", include(login_urls)),
]
