from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from dj_waanverse_auth.utils.security.cookies import (
    build_auth_response,
    clear_auth_cookies,
    is_mobile_client,
    set_auth_cookies,
)
from dj_waanverse_auth.utils.security.tokens import IssuedTokens

factory = APIRequestFactory()
COOKIES_MODULE = "dj_waanverse_auth.utils.security.cookies.auth_config"


def _fake_tokens() -> IssuedTokens:
    now = timezone.now()
    return IssuedTokens(
        access_token="fake-access-token",
        refresh_token="fake-refresh-token",
        access_expires_at=now + timedelta(minutes=30),
        refresh_expires_at=now + timedelta(days=30),
        session_id="session-123",
    )


def _drf_request(headers=None):
    return Request(factory.post("/verify/", {}, **(headers or {})))


class IsMobileClientTests(TestCase):
    def test_true_when_header_present_case_insensitive(self):
        self.assertTrue(
            is_mobile_client(_drf_request({"HTTP_X_CLIENT_TYPE": "Mobile"}))
        )

    def test_false_when_header_missing(self):
        self.assertFalse(is_mobile_client(_drf_request()))

    def test_false_for_unrecognized_value(self):
        self.assertFalse(is_mobile_client(_drf_request({"HTTP_X_CLIENT_TYPE": "web"})))


@override_settings(DEBUG=True)
class SetAuthCookiesTests(TestCase):
    def test_sets_both_cookies_httponly_with_correct_values(self):
        response = Response({})
        set_auth_cookies(response, _fake_tokens())

        self.assertEqual(response.cookies["access_token"].value, "fake-access-token")
        self.assertEqual(response.cookies["refresh_token"].value, "fake-refresh-token")
        self.assertTrue(response.cookies["access_token"]["httponly"])
        self.assertTrue(response.cookies["refresh_token"]["httponly"])

    def test_defaults_to_insecure_when_debug_true(self):
        response = Response({})
        set_auth_cookies(response, _fake_tokens())
        self.assertFalse(response.cookies["access_token"]["secure"])

    @patch(f"{COOKIES_MODULE}.cookie_secure", True)
    def test_explicit_setting_overrides_debug_default(self):
        response = Response({})
        set_auth_cookies(response, _fake_tokens())
        self.assertTrue(response.cookies["access_token"]["secure"])


class ClearAuthCookiesTests(TestCase):
    def test_deletes_both_cookies(self):
        response = Response({})
        clear_auth_cookies(response)

        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        self.assertEqual(response.cookies["access_token"].value, "")


class BuildAuthResponseTests(TestCase):
    def test_web_client_body_excludes_raw_tokens(self):
        response = build_auth_response(
            _drf_request(), _fake_tokens(), {"msg": "ok"}, 200
        )

        self.assertNotIn("access_token", response.data)
        self.assertNotIn("refresh_token", response.data)
        self.assertIn("access_token", response.cookies)

    def test_mobile_client_body_includes_raw_tokens(self):
        request = _drf_request({"HTTP_X_CLIENT_TYPE": "mobile"})
        response = build_auth_response(request, _fake_tokens(), {"msg": "ok"}, 200)

        self.assertEqual(response.data["access_token"], "fake-access-token")
        self.assertEqual(response.data["refresh_token"], "fake-refresh-token")
        self.assertIn("access_token_expires_in", response.data)
        self.assertIn("refresh_token_expires_in", response.data)

    def test_mobile_client_also_receives_cookies(self):
        request = _drf_request({"HTTP_X_CLIENT_TYPE": "mobile"})
        response = build_auth_response(request, _fake_tokens(), {"msg": "ok"}, 200)

        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)

    def test_status_code_applied(self):
        response = build_auth_response(
            _drf_request(), _fake_tokens(), {"msg": "ok"}, 201
        )
        self.assertEqual(response.status_code, 201)
