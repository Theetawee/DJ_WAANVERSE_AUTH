from __future__ import annotations

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from dj_waanverse_auth.utils.security.csrf import (
    CSRF_COOKIE_NAME,
    csrf_is_valid,
    generate_csrf_token,
    get_csrf_cookie,
    get_csrf_header,
)

factory = APIRequestFactory()


def _request(cookie=None, header=None, method="POST"):
    kwargs = {"HTTP_X_CSRF_TOKEN": header} if header else {}
    django_request = getattr(factory, method.lower())("/", **kwargs)
    if cookie is not None:
        django_request.COOKIES[CSRF_COOKIE_NAME] = cookie
    return django_request


class GenerateCsrfTokenTests(TestCase):
    def test_returns_a_nonempty_string(self):
        self.assertTrue(generate_csrf_token())

    def test_generates_unique_values(self):
        self.assertNotEqual(generate_csrf_token(), generate_csrf_token())

    def test_reasonably_long(self):
        self.assertGreater(len(generate_csrf_token()), 20)


class GetCsrfCookieTests(TestCase):
    def test_returns_value_when_present(self):
        request = _request(cookie="abc123")
        self.assertEqual(get_csrf_cookie(request), "abc123")

    def test_returns_none_when_absent(self):
        request = _request()
        self.assertIsNone(get_csrf_cookie(request))


class GetCsrfHeaderTests(TestCase):
    def test_returns_value_when_present(self):
        request = _request(header="abc123")
        self.assertEqual(get_csrf_header(request), "abc123")

    def test_returns_none_when_absent(self):
        request = _request()
        self.assertIsNone(get_csrf_header(request))

    def test_strips_whitespace(self):
        request = _request(header="  abc123  ")
        self.assertEqual(get_csrf_header(request), "abc123")


class CsrfIsValidTests(TestCase):
    def test_true_when_cookie_and_header_match(self):
        request = _request(cookie="token-value", header="token-value")
        self.assertTrue(csrf_is_valid(request))

    def test_false_when_values_differ(self):
        request = _request(cookie="token-a", header="token-b")
        self.assertFalse(csrf_is_valid(request))

    def test_false_when_cookie_missing(self):
        request = _request(header="token-value")
        self.assertFalse(csrf_is_valid(request))

    def test_false_when_header_missing(self):
        request = _request(cookie="token-value")
        self.assertFalse(csrf_is_valid(request))

    def test_false_when_both_missing(self):
        request = _request()
        self.assertFalse(csrf_is_valid(request))

    def test_false_when_both_empty_strings(self):
        request = _request(cookie="", header="")
        self.assertFalse(csrf_is_valid(request))
