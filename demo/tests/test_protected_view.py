# tests/test_protected_view_integration.py
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework.views import APIView

from dj_waanverse_auth.authentication import JWTAuthentication
from dj_waanverse_auth.utils.security.csrf import CSRF_COOKIE_NAME
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache
from dj_waanverse_auth.utils.security.tokens import issue_tokens_for_account
from tests.utils import generate_rsa_keypair_files

Account = get_user_model()
KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"


class _WhoAmIView(APIView):
    """Minimal stand-in for what LogoutView will look like: protected,
    reads request.user/request.auth once authenticated."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {"account_id": request.user.pk, "session_id": request.auth["sid"]}
        )

    def post(self, request):
        return Response(
            {"account_id": request.user.pk, "session_id": request.auth["sid"]}
        )


urlpatterns = [path("whoami/", _WhoAmIView.as_view())]


class ProtectedViewIntegrationTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._urlconf_patcher = patch("django.conf.settings.ROOT_URLCONF", __name__)
        cls._urlconf_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls._urlconf_patcher.stop()
        super().tearDownClass()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        private_path, public_path = generate_rsa_keypair_files(Path(self._tmp.name))
        self.patchers = [
            patch(f"{KEYS_MODULE}.private_key_path", private_path),
            patch(f"{KEYS_MODULE}.public_key_path", public_path),
        ]
        for p in self.patchers:
            p.start()
        clear_key_cache()

        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        self.tokens = issue_tokens_for_account(self.account, request=None)

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        clear_key_cache()
        self._tmp.cleanup()

    # ------------------------------------------------------------------
    # Unauthenticated is genuinely rejected by the pipeline
    # ------------------------------------------------------------------

    def test_no_token_returns_401(self):
        response = self.client.get("/whoami/")
        self.assertEqual(response.status_code, 401)

    def test_invalid_token_returns_401_not_500(self):
        self.client.cookies["access_token"] = "garbage"
        response = self.client.get("/whoami/")
        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------
    # request.user / request.auth populate correctly
    # ------------------------------------------------------------------

    def test_valid_bearer_token_populates_request_user_and_auth(self):
        response = self.client.get(
            "/whoami/", HTTP_AUTHORIZATION=f"Bearer {self.tokens.access_token}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["account_id"], self.account.pk)
        self.assertEqual(response.data["session_id"], self.tokens.session_id)

    def test_valid_cookie_token_on_get_populates_request_user(self):
        self.client.cookies["access_token"] = self.tokens.access_token
        response = self.client.get("/whoami/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["account_id"], self.account.pk)

    # ------------------------------------------------------------------
    # CSRF actually enforced through the real pipeline, not just the unit
    # ------------------------------------------------------------------

    def test_cookie_token_on_post_without_csrf_is_403_not_401(self):
        """
        Confirms PermissionDenied (CSRF failure) surfaces as 403,
        distinct from AuthenticationFailed's 401 — DRF maps the two
        exceptions to different status codes, and that distinction
        needs to survive all the way through the real pipeline.
        """
        self.client.cookies["access_token"] = self.tokens.access_token
        response = self.client.post("/whoami/")
        self.assertEqual(response.status_code, 403)

    def test_cookie_token_on_post_with_valid_csrf_succeeds(self):
        self.client.cookies["access_token"] = self.tokens.access_token
        self.client.cookies[CSRF_COOKIE_NAME] = "matching-token"
        response = self.client.post("/whoami/", HTTP_X_CSRF_TOKEN="matching-token")
        self.assertEqual(response.status_code, 200)

    def test_bearer_token_on_post_never_needs_csrf(self):
        response = self.client.post(
            "/whoami/", HTTP_AUTHORIZATION=f"Bearer {self.tokens.access_token}"
        )
        self.assertEqual(response.status_code, 200)
