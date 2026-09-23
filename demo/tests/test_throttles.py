from __future__ import annotations

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser

from dj_waanverse_auth.throttles import BaseIdentifierThrottle, BaseIPThrottle

factory = APIRequestFactory()


class _TestIPThrottle(BaseIPThrottle):
    scope = "test-ip-scope"


class _TestIdentifierThrottle(BaseIdentifierThrottle):
    scope = "test-identifier-scope"


TEST_THROTTLE_RATES = {
    "test-ip-scope": "10/hour",
    "test-identifier-scope": "10/hour",
    "custom-field-scope": "10/hour",
    "different-scope": "10/hour",
}


class ThrottleTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # SimpleRateThrottle reads rates from its class attribute.
        # Temporarily add only the scopes used by these tests.
        cls._original_throttle_rates = SimpleRateThrottle.THROTTLE_RATES

        SimpleRateThrottle.THROTTLE_RATES = {
            **cls._original_throttle_rates,
            **TEST_THROTTLE_RATES,
        }

    @classmethod
    def tearDownClass(cls):
        # Restore the original DRF throttle configuration so that
        # other tests are completely unaffected.
        SimpleRateThrottle.THROTTLE_RATES = cls._original_throttle_rates

        super().tearDownClass()

    def setUp(self):
        cache.clear()


def _drf_request(data=None, ip_address=None):
    django_request = factory.post(
        "/",
        data or {},
        format="json",
    )

    if ip_address is not None:
        django_request.ip_address = ip_address

    return Request(
        django_request,
        parsers=[JSONParser(), FormParser(), MultiPartParser()],
    )


class BaseIPThrottleTests(ThrottleTestCase):

    def test_raises_if_ip_address_missing(self):
        request = _drf_request()
        throttle = _TestIPThrottle()

        with self.assertRaises(ImproperlyConfigured):
            throttle.get_cache_key(request, view=None)

    def test_cache_key_stable_for_same_ip(self):
        throttle = _TestIPThrottle()

        key_a = throttle.get_cache_key(
            _drf_request(ip_address="203.0.113.5"),
            view=None,
        )

        key_b = throttle.get_cache_key(
            _drf_request(ip_address="203.0.113.5"),
            view=None,
        )

        self.assertEqual(key_a, key_b)

    def test_cache_key_differs_for_different_ips(self):
        throttle = _TestIPThrottle()

        key_a = throttle.get_cache_key(
            _drf_request(ip_address="203.0.113.5"),
            view=None,
        )

        key_b = throttle.get_cache_key(
            _drf_request(ip_address="198.51.100.9"),
            view=None,
        )

        self.assertNotEqual(key_a, key_b)

    def test_different_scopes_produce_different_keys_for_same_ip(self):
        class _OtherScopeThrottle(BaseIPThrottle):
            scope = "different-scope"

        request = _drf_request(ip_address="203.0.113.5")

        key_a = _TestIPThrottle().get_cache_key(
            request,
            view=None,
        )

        key_b = _OtherScopeThrottle().get_cache_key(
            request,
            view=None,
        )

        self.assertNotEqual(key_a, key_b)


class BaseIdentifierThrottleTests(ThrottleTestCase):

    def test_returns_none_when_identifier_missing(self):
        throttle = _TestIdentifierThrottle()

        self.assertIsNone(
            throttle.get_cache_key(
                _drf_request(),
                view=None,
            )
        )

    def test_returns_none_when_identifier_blank(self):
        throttle = _TestIdentifierThrottle()

        request = _drf_request(
            {
                "identifier": "   ",
            }
        )

        self.assertIsNone(
            throttle.get_cache_key(
                request,
                view=None,
            )
        )

    def test_normalizes_case_and_whitespace(self):
        throttle = _TestIdentifierThrottle()

        key_a = throttle.get_cache_key(
            _drf_request(
                {
                    "identifier": "  Target@Example.com  ",
                }
            ),
            view=None,
        )

        key_b = throttle.get_cache_key(
            _drf_request(
                {
                    "identifier": "target@example.com",
                }
            ),
            view=None,
        )

        self.assertEqual(key_a, key_b)

    def test_different_identifiers_produce_different_keys(self):
        throttle = _TestIdentifierThrottle()

        key_a = throttle.get_cache_key(
            _drf_request(
                {
                    "identifier": "a@example.com",
                }
            ),
            view=None,
        )

        key_b = throttle.get_cache_key(
            _drf_request(
                {
                    "identifier": "b@example.com",
                }
            ),
            view=None,
        )

        self.assertNotEqual(key_a, key_b)

    def test_respects_custom_identifier_field(self):
        class _CustomFieldThrottle(BaseIdentifierThrottle):
            scope = "custom-field-scope"
            IDENTIFIER_FIELD = "email"

        throttle = _CustomFieldThrottle()

        request = _drf_request(
            {
                "email": "a@example.com",
            }
        )

        self.assertIsNotNone(
            throttle.get_cache_key(
                request,
                view=None,
            )
        )


class _UnconfiguredThrottle(BaseIPThrottle):
    scope = "no-such-scope"

    def test_unconfigured_scope_never_throttles(self):
        throttle = _UnconfiguredThrottle()
        request = _drf_request(ip_address="203.0.113.5")
        self.assertTrue(throttle.allow_request(request, view=None))
