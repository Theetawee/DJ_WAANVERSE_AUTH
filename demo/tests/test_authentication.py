from __future__ import annotations

import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from dj_waanverse_auth.authentication import (
    JWTAuthentication,
    enforce_csrf_if_cookie_sourced,
    extract_bearer_token,
    get_access_token,
    get_refresh_token,
)
from dj_waanverse_auth.utils.security.csrf import CSRF_COOKIE_NAME
from dj_waanverse_auth.utils.security.jwt import ACCESS, REFRESH, encode_token
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache
from tests.utils import generate_rsa_keypair_files, tamper_jwt_signature

Account = get_user_model()
factory = APIRequestFactory()
KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"


def _request(cookies=None, bearer=None, csrf_header=None, method="get"):
    kwargs = {}
    if bearer:
        kwargs["HTTP_AUTHORIZATION"] = f"Bearer {bearer}"
    if csrf_header:
        kwargs["HTTP_X_CSRF_TOKEN"] = csrf_header

    django_request = getattr(factory, method)("/", **kwargs)
    if cookies:
        django_request.COOKIES.update(cookies)
    return Request(django_request)


class ExtractBearerTokenTests(TestCase):
    def test_extracts_token_after_bearer_prefix(self):
        self.assertEqual(extract_bearer_token(_request(bearer="abc123")), "abc123")

    def test_returns_none_when_header_missing(self):
        self.assertIsNone(extract_bearer_token(_request()))

    def test_returns_none_for_non_bearer_scheme(self):
        django_request = factory.get("/", HTTP_AUTHORIZATION="Basic abc123")
        self.assertIsNone(extract_bearer_token(Request(django_request)))

    def test_returns_none_for_empty_token_after_bearer(self):
        django_request = factory.get("/", HTTP_AUTHORIZATION="Bearer ")
        self.assertIsNone(extract_bearer_token(Request(django_request)))


class GetAccessTokenTests(TestCase):
    def test_cookie_returns_cookie_source(self):
        token, source = get_access_token(
            _request(cookies={"access_token": "from-cookie"})
        )
        self.assertEqual(token, "from-cookie")
        self.assertEqual(source, "cookie")

    def test_bearer_returns_bearer_source(self):
        token, source = get_access_token(_request(bearer="from-header"))
        self.assertEqual(token, "from-header")
        self.assertEqual(source, "bearer")

    def test_cookie_takes_priority_over_bearer(self):
        token, source = get_access_token(
            _request(cookies={"access_token": "from-cookie"}, bearer="from-header")
        )
        self.assertEqual(token, "from-cookie")
        self.assertEqual(source, "cookie")

    def test_returns_none_none_when_neither_present(self):
        self.assertEqual(get_access_token(_request()), (None, None))


class GetRefreshTokenTests(TestCase):
    def test_cookie_returns_cookie_source(self):
        token, source = get_refresh_token(
            _request(cookies={"refresh_token": "from-cookie"})
        )
        self.assertEqual(token, "from-cookie")
        self.assertEqual(source, "cookie")

    def test_bearer_returns_bearer_source(self):
        token, source = get_refresh_token(_request(bearer="from-header"))
        self.assertEqual(token, "from-header")
        self.assertEqual(source, "bearer")

    def test_access_and_refresh_cookies_are_independent(self):
        request = _request(cookies={"access_token": "a", "refresh_token": "r"})
        self.assertEqual(get_access_token(request)[0], "a")
        self.assertEqual(get_refresh_token(request)[0], "r")


class EnforceCsrfIfCookieSourcedTests(TestCase):
    def test_noop_for_bearer_source(self):
        request = _request(bearer="x", method="post")
        enforce_csrf_if_cookie_sourced(request, "bearer")  # should not raise

    def test_noop_for_safe_method_even_when_cookie_sourced(self):
        request = _request(cookies={"access_token": "x"}, method="get")
        enforce_csrf_if_cookie_sourced(request, "cookie")  # should not raise

    def test_raises_for_cookie_source_unsafe_method_no_csrf_header(self):
        request = _request(cookies={"access_token": "x"}, method="post")
        with self.assertRaises(PermissionDenied):
            enforce_csrf_if_cookie_sourced(request, "cookie")

    def test_raises_when_csrf_header_present_but_no_matching_cookie(self):
        request = _request(
            cookies={"access_token": "x"}, csrf_header="some-token", method="post"
        )
        with self.assertRaises(PermissionDenied):
            enforce_csrf_if_cookie_sourced(request, "cookie")

    def test_passes_when_csrf_cookie_and_header_match(self):
        request = _request(
            cookies={"access_token": "x", CSRF_COOKIE_NAME: "matching-token"},
            csrf_header="matching-token",
            method="post",
        )
        enforce_csrf_if_cookie_sourced(request, "cookie")  # should not raise

    def test_raises_when_csrf_cookie_and_header_mismatch(self):
        request = _request(
            cookies={"access_token": "x", CSRF_COOKIE_NAME: "cookie-value"},
            csrf_header="different-value",
            method="post",
        )
        with self.assertRaises(PermissionDenied):
            enforce_csrf_if_cookie_sourced(request, "cookie")


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
    # No token
    # ------------------------------------------------------------------

    def test_returns_none_when_no_token_supplied(self):
        self.assertIsNone(self.auth.authenticate(_request()))

    # ------------------------------------------------------------------
    # Happy paths — GET requests, no CSRF needed regardless of source
    # ------------------------------------------------------------------

    def test_authenticates_via_cookie_on_safe_method(self):
        token = self._access_token()
        account, payload = self.auth.authenticate(
            _request(cookies={"access_token": token}, method="get")
        )
        self.assertEqual(account.pk, self.account.pk)
        self.assertEqual(payload["sub"], str(self.account.pk))

    def test_authenticates_via_bearer_on_safe_method(self):
        token = self._access_token()
        account, _ = self.auth.authenticate(_request(bearer=token, method="get"))
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
            _request(
                cookies={"access_token": cookie_token},
                bearer=header_token,
                method="get",
            )
        )
        self.assertEqual(account.pk, self.account.pk)

    def test_authenticate_header_returns_bearer(self):
        self.assertEqual(self.auth.authenticate_header(_request()), "Bearer")

    # ------------------------------------------------------------------
    # CSRF — cookie-sourced, unsafe methods
    # ------------------------------------------------------------------

    def test_cookie_sourced_post_without_csrf_header_raises(self):
        token = self._access_token()
        with self.assertRaises(PermissionDenied):
            self.auth.authenticate(
                _request(cookies={"access_token": token}, method="post")
            )

    def test_cookie_sourced_post_with_matching_csrf_succeeds(self):
        token = self._access_token()
        request = _request(
            cookies={"access_token": token, CSRF_COOKIE_NAME: "matching-token"},
            csrf_header="matching-token",
            method="post",
        )
        account, _ = self.auth.authenticate(request)
        self.assertEqual(account.pk, self.account.pk)

    def test_cookie_sourced_post_with_mismatched_csrf_raises(self):
        token = self._access_token()
        request = _request(
            cookies={"access_token": token, CSRF_COOKIE_NAME: "cookie-token"},
            csrf_header="different-token",
            method="post",
        )
        with self.assertRaises(PermissionDenied):
            self.auth.authenticate(request)

    def test_bearer_sourced_post_never_requires_csrf(self):
        """The mobile path: Authorization header, no cookies, no CSRF token anywhere."""
        token = self._access_token()
        account, _ = self.auth.authenticate(_request(bearer=token, method="post"))
        self.assertEqual(account.pk, self.account.pk)

    def test_bearer_sourced_post_succeeds_even_if_csrf_cookie_happens_to_exist(self):
        """
        A stray CSRF cookie from a previous session shouldn't matter
        for a bearer-authenticated request — CSRF only applies when
        the AUTH token itself came from a cookie.
        """
        token = self._access_token()
        request = _request(
            bearer=token,
            cookies={CSRF_COOKIE_NAME: "leftover-value"},
            method="post",
        )
        account, _ = self.auth.authenticate(request)
        self.assertEqual(account.pk, self.account.pk)

    def test_invalid_token_raises_before_csrf_is_even_checked(self):
        """
        Token validity is checked before CSRF — an attacker shouldn't
        learn anything about CSRF state from an already-invalid token.
        """
        request = _request(cookies={"access_token": "garbage"}, method="post")
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    # ------------------------------------------------------------------
    # Invalid tokens
    # ------------------------------------------------------------------

    def test_expired_token_raises(self):
        token = self._access_token(lifetime=timedelta(seconds=-1))
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(_request(cookies={"access_token": token}))

    def test_tampered_token_raises(self):
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
