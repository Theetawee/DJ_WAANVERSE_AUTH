# dj_waanverse_auth/urls.py — additions
from dj_waanverse_auth.views.session_views import (
    RevokeOtherSessionsView,
    SessionListView,
    SessionRevokeView,
)
from django.urls import path

urlpatterns = [
    path("", SessionListView.as_view(), name="dj_waanverse_auth_sessions"),
    path(
        "<uuid:session_id>/revoke/",
        SessionRevokeView.as_view(),
        name="dj_waanverse_auth_session_revoke",
    ),
    path(
        "revoke-others/",
        RevokeOtherSessionsView.as_view(),
        name="dj_waanverse_auth_revoke_other_sessions",
    ),
]
