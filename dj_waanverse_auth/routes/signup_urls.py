from django.urls import path

from dj_waanverse_auth.views.signup_views import (
    signup_view,
)

urlpatterns = [
    path("", signup_view, name="dj_waanverse_auth_signup"),
]
