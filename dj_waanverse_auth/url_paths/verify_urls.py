from django.urls import path
from dj_waanverse_auth.views.verify_views import RequestVerificationView

urlpatterns = [
    path(
        "request/",
        RequestVerificationView.as_view(),
        name="dj_waanverse_auth_request_verification",
    ),
]
