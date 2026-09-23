# dj_waanverse_auth/views/session_views.py
from __future__ import annotations

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from dj_waanverse_auth.throttles import SessionActionsThrottle
from dj_waanverse_auth.authentication import JWTAuthentication
from dj_waanverse_auth.models import Session


def _current_session_id(request) -> str | None:
    return request.auth.get("sid") if request.auth else None


def _serialize_session(session: Session, current_session_id: str | None) -> dict:
    return {
        "id": str(session.id),
        "user_agent": session.user_agent,
        "ip_address": session.ip_address,
        "created_at": session.created_at.isoformat(),
        "last_used_at": session.last_used_at.isoformat(),
        "is_current": str(session.id) == current_session_id,
    }


class SessionListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [SessionActionsThrottle]

    def get(self, request):
        current_session_id = _current_session_id(request)
        sessions = Session.objects.filter(
            account=request.user, is_revoked=False
        ).order_by("-last_used_at")

        return Response(
            {"sessions": [_serialize_session(s, current_session_id) for s in sessions]},
            status=status.HTTP_200_OK,
        )


class SessionRevokeView(APIView):
    """
    Revokes one specific session belonging to the authenticated
    account. Always 404s — never 403 — whether the session id
    doesn't exist at all OR belongs to a different account. The
    query filters on account=request.user directly, so those two
    cases are structurally indistinguishable to this view; that's
    deliberate, so this endpoint can't be used to probe which
    session ids exist for other users.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [SessionActionsThrottle]

    def post(self, request, session_id):
        session = Session.objects.filter(
            pk=session_id, account=request.user, is_revoked=False
        ).first()

        if session is None:
            return Response(
                {"msg": "Session not found."}, status=status.HTTP_404_NOT_FOUND
            )

        session.revoke()
        return Response({"msg": "Session revoked."}, status=status.HTTP_200_OK)


class RevokeOtherSessionsView(APIView):
    """ "Log out all other devices" — keeps the session making this request alive."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [SessionActionsThrottle]

    def post(self, request):
        current_session_id = _current_session_id(request)

        updated = (
            Session.objects.filter(account=request.user, is_revoked=False)
            .exclude(pk=current_session_id)
            .update(is_revoked=True, revoked_at=timezone.now())
        )

        return Response(
            {"msg": f"Revoked {updated} other session(s)."}, status=status.HTTP_200_OK
        )
