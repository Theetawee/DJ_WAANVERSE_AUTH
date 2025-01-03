from django.urls import include, path

from dj_waanverse_auth.routes import authorization_urls, login_urls, mfa_urls

urlpatterns = [
    path("login/", include(login_urls)),
    path("", include(authorization_urls)),
    path("mfa/", include(mfa_urls)),
]
