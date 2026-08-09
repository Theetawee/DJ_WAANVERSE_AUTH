from dj_waanverse_auth.views.signup_views import SignupView
from django.urls import path

url_patterns = [path("", SignupView.as_view(), name="dj_waanverse_auth_signup")]
