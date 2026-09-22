from django.urls import path, include
from dj_waanverse_auth.url_paths import (
    signup_urls,
    verify_urls,
    login_urls,
    refresh_urls,
    logout_urls,
)

urlpatterns = [
    path("signup/", include(signup_urls.url_patterns)),
    path("verify/", include(verify_urls.urlpatterns)),
    path("login/", include(login_urls.url_patterns)),
    path("refresh/", include(refresh_urls.url_patterns)),
    path("logout/", include(logout_urls.url_patterns)),
]
