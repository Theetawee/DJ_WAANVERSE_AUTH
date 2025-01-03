from django.urls import path

from dj_waanverse_auth.views.mfa_views import activate_mfa_view, deactivate_mfa_view

urlpatterns = [
    path("activate/", activate_mfa_view, name="mfa_activate"),
    path("deactivate/", deactivate_mfa_view, name="mfa_deactivate"),
]
