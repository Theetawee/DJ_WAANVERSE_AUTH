# tests/test_authentication.py
from __future__ import annotations

import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from dj_waanverse_auth.authentication import (
    JWTAuthentication,
    extract_bearer_token,
    get_access_token,
    get_refresh_token,
)
from dj_waanverse_auth.utils.security.jwt import ACCESS, REFRESH, encode_token
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache
from tests.utils import generate_rsa_keypair_files

Account = get_user_model()
factory = APIRequestFactory()
KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"


def _request(cookies=None, bearer=None):
    django_request = factory.get("/")
    if cookies:
        django_request.COOKIES.update(cookies)
    kwargs = {}
    if bearer:
        kwargs["HTTP_AUTHORIZATION"] = f"Bearer {bearer}"
    django_request = factory.get("/", **kwargs)
    if cookies:
        django_request.COOKIES.update(cookies)
    return Request(django_request)


class ExtractBearerTokenTests(TestCase):
    def test_extracts_token_after_bearer_prefix(self):
        request = _request(bearer="abc123")
        self.assertEqual(extract_bearer_token(request), "abc123")

    def test_returns_none_when_header_missing(self):
        request = _request()
        self.assertIsNone(extract_bearer_token(request))

    def test_returns_none_for_non_bearer_scheme(self):
        request = factory.get("/", HTTP_AUTHORIZATION="Basic abc123")
        self.assertIsNone(extract_bearer_token(Request(request)))

    def test_returns_none_for_empty_token_after_bearer(self):
        request = factory.get("/", HTTP_AUTHORIZATION="Bearer ")
        self.assertIsNone(extract_bearer_token(Request(request)))


class GetAccessTokenTests(TestCase):
    def test_prefers_cookie_over_bearer_header(self):
        request = _request(
            cookies={"access_token": "from-cookie"}, bearer="from-header"
        )
        self.assertEqual(get_access_token(request), "from-cookie")

    def test_falls_back_to_bearer_when_no_cookie(self):
        request = _request(bearer="from-header")
        self.assertEqual(get_access_token(request), "from-header")

    def test_returns_none_when_neither_present(self):
        request = _request()
        self.assertIsNone(get_access_token(request))


class GetRefreshTokenTests(TestCase):
    def test_prefers_cookie_over_bearer_header(self):
        request = _request(
            cookies={"refresh_token": "from-cookie"}, bearer="from-header"
        )
        self.assertEqual(get_refresh_token(request), "from-cookie")

    def test_falls_back_to_bearer_when_no_cookie(self):
        request = _request(bearer="from-header")
        self.assertEqual(get_refresh_token(request), "from-header")

    def test_access_and_refresh_cookies_are_independent(self):
        request = _request(cookies={"access_token": "a", "refresh_token": "r"})
        self.assertEqual(get_access_token(request), "a")
        self.assertEqual(get_refresh_token(request), "r")


class JWTAuthenticationTests(TestCase):
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
        self.auth = JWTAuthentication()

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        clear_key_cache()
        self._tmp.cleanup()

    def _access_token(self, **overrides):
        kwargs = dict(
            account_id=self.account.pk,
            session_id="s1",
            token_type=ACCESS,
            lifetime=timedelta(minutes=30),
        )
        kwargs.update(overrides)
        token, _, _ = encode_token(**kwargs)
        return token

    # ------------------------------------------------------------------
    # No token present
    # ------------------------------------------------------------------

    def test_returns_none_when_no_token_supplied(self):
        result = self.auth.authenticate(_request())
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_authenticates_via_cookie(self):
        token = self._access_token()
        account, payload = self.auth.authenticate(
            _request(cookies={"access_token": token})
        )

        self.assertEqual(account.pk, self.account.pk)
        self.assertEqual(payload["sub"], str(self.account.pk))

    def test_authenticates_via_bearer_header_when_no_cookie(self):
        token = self._access_token()
        account, _ = self.auth.authenticate(_request(bearer=token))
        self.assertEqual(account.pk, self.account.pk)

    def test_cookie_takes_priority_over_bearer_when_both_present(self):
        cookie_token = self._access_token()
        other_account = Account.objects.create_user(
            email_address="other@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        header_token = self._access_token(account_id=other_account.pk)

        account, _ = self.auth.authenticate(
            _request(cookies={"access_token": cookie_token}, bearer=header_token)
        )
        self.assertEqual(account.pk, self.account.pk)

    def test_authenticate_header_returns_bearer(self):
        self.assertEqual(self.auth.authenticate_header(_request()), "Bearer")

    # ------------------------------------------------------------------
    # Invalid tokens — must raise, never silently return None
    # ------------------------------------------------------------------

    def test_expired_token_raises(self):
        token = self._access_token(lifetime=timedelta(seconds=-1))
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(_request(cookies={"access_token": token}))

    def test_tampered_token_raises(self):
        from tests.utils import tamper_jwt_signature

        token = tamper_jwt_signature(self._access_token())
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(_request(cookies={"access_token": token}))

    def test_refresh_token_used_as_access_token_raises(self):
        token, _, _ = encode_token(
            account_id=self.account.pk,
            session_id="s1",
            token_type=REFRESH,
            lifetime=timedelta(days=1),
        )
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(_request(cookies={"access_token": token}))

    def test_garbage_token_raises(self):
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(_request(cookies={"access_token": "not-a-real-jwt"}))

    # ------------------------------------------------------------------
    # Account state
    # ------------------------------------------------------------------

    def test_token_for_nonexistent_account_raises(self):
        token = self._access_token(account_id=999999)
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(_request(cookies={"access_token": token}))

    def test_token_for_inactive_account_raises(self):
        self.account.is_active = False
        self.account.save(update_fields=["is_active"])

        token = self._access_token()
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(_request(cookies={"access_token": token}))
