from django.urls import path
from dj_waanverse_auth.views.login_views import authenticate_account

urlpatterns = [
    path("", authenticate_account, name="dj_waanverse_auth_auth"),
]
