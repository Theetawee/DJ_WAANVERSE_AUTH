from django.urls import path, include
from dj_waanverse_auth.url_paths import signup_urls

urlpatterns = [path("signup/", include(signup_urls.url_patterns))]
