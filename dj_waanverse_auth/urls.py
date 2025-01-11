from django.urls import include, path

from dj_waanverse_auth.routes import (
    authorization_urls,
    login_urls,
    mfa_urls,
    password_urls,
    signup_urls,
)

urlpatterns = [
    path("login/", include(login_urls)),
    path("", include(authorization_urls)),
    path("mfa/", include(mfa_urls)),
    path("signup/", include(signup_urls)),
    path("password/", include(password_urls)),
]
