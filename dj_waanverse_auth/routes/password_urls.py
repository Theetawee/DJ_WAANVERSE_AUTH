from django.urls import path

from dj_waanverse_auth.views.password_reset_views import (
    initiate_password_reset_view,
    reset_password_view,
)

urlpatterns = [
    path(
        "reset/",
        initiate_password_reset_view,
        name="dj_waanverse_auth_initiate_password_reset",
    ),
    path(
        "new-password/",
        reset_password_view,
        name="dj_waanverse_auth_reset_password",
    ),
]
