# tests/test_ip_client_middleware.py
from __future__ import annotations

from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from dj_waanverse_auth.middleware import IPAddressMiddleware

factory = RequestFactory()
MODULE = "dj_waanverse_auth.middleware.client_ip"
TEST_CLOUDFLARE_RANGES = [
    "203.0.113.0/24"
]  # TEST-NET-3 — safe, documented-reserved test range

CLOUDFLARE_PEER = "203.0.113.5"
NON_TRUSTED_PEER = "198.51.100.9"
LOCALHOST_PEER = "127.0.0.1"


def _get_response(request):
    return HttpResponse("ok")


class CloudflareOnlyModeTests(TestCase):
    """trust_cloudflare_only=True — localhost is NOT trusted."""

    def setUp(self):
        self.cf_patcher = patch(
            f"{MODULE}.CLOUDFLARE_IP_RANGES", TEST_CLOUDFLARE_RANGES
        )
        self.cf_patcher.start()
        self.addCleanup(self.cf_patcher.stop)

        self.trust_patcher = patch(f"{MODULE}.auth_config.trust_cloudflare_only", True)
        self.trust_patcher.start()
        self.addCleanup(self.trust_patcher.stop)

        self.middleware = IPAddressMiddleware(_get_response)

    def test_no_localhost_networks_loaded(self):
        self.assertEqual(len(self.middleware.localhost_networks), 0)

    def test_cf_connecting_ip_trusted_from_cloudflare_peer(self):
        request = factory.get(
            "/", REMOTE_ADDR=CLOUDFLARE_PEER, HTTP_CF_CONNECTING_IP="198.51.100.9"
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, "198.51.100.9")

    def test_cf_connecting_ip_preferred_over_x_forwarded_for(self):
        request = factory.get(
            "/",
            REMOTE_ADDR=CLOUDFLARE_PEER,
            HTTP_CF_CONNECTING_IP="198.51.100.9",
            HTTP_X_FORWARDED_FOR="1.2.3.4, 9.9.9.9",
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, "198.51.100.9")

    def test_falls_back_to_x_forwarded_for_last_entry_when_no_cf_header(self):
        request = factory.get(
            "/",
            REMOTE_ADDR=CLOUDFLARE_PEER,
            HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8, 198.51.100.9",
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, "198.51.100.9")

    def test_invalid_cf_header_falls_through_to_x_forwarded_for(self):
        request = factory.get(
            "/",
            REMOTE_ADDR=CLOUDFLARE_PEER,
            HTTP_CF_CONNECTING_IP="garbage",
            HTTP_X_FORWARDED_FOR="198.51.100.9",
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, "198.51.100.9")

    def test_localhost_peer_headers_ignored_when_cloudflare_only(self):
        request = factory.get(
            "/", REMOTE_ADDR=LOCALHOST_PEER, HTTP_X_FORWARDED_FOR="198.51.100.9"
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, LOCALHOST_PEER)  # header ignored entirely

    def test_untrusted_peer_headers_ignored(self):
        request = factory.get(
            "/",
            REMOTE_ADDR=NON_TRUSTED_PEER,
            HTTP_X_FORWARDED_FOR="9.9.9.9",
            HTTP_CF_CONNECTING_IP="9.9.9.9",
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, NON_TRUSTED_PEER)

    def test_request_always_passes_through(self):
        request = factory.get(
            "/", REMOTE_ADDR=NON_TRUSTED_PEER, HTTP_X_FORWARDED_FOR="garbage"
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)


class LocalhostAlsoTrustedModeTests(TestCase):
    """trust_cloudflare_only=False — localhost trusted too (single local proxy setups)."""

    def setUp(self):
        self.cf_patcher = patch(
            f"{MODULE}.CLOUDFLARE_IP_RANGES", TEST_CLOUDFLARE_RANGES
        )
        self.cf_patcher.start()
        self.addCleanup(self.cf_patcher.stop)

        self.trust_patcher = patch(f"{MODULE}.auth_config.trust_cloudflare_only", False)
        self.trust_patcher.start()
        self.addCleanup(self.trust_patcher.stop)

        self.middleware = IPAddressMiddleware(_get_response)

    def test_localhost_networks_loaded(self):
        self.assertGreater(len(self.middleware.localhost_networks), 0)

    def test_localhost_peer_x_forwarded_for_last_entry_trusted(self):
        request = factory.get(
            "/",
            REMOTE_ADDR=LOCALHOST_PEER,
            HTTP_X_FORWARDED_FOR="1.2.3.4, 198.51.100.9",
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, "198.51.100.9")

    def test_ipv6_localhost_trusted(self):
        request = factory.get(
            "/", REMOTE_ADDR="::1", HTTP_X_FORWARDED_FOR="198.51.100.9"
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, "198.51.100.9")

    def test_cf_connecting_ip_ignored_from_localhost_peer(self):
        """CF-Connecting-IP is only meaningful from a REAL Cloudflare peer."""
        request = factory.get(
            "/",
            REMOTE_ADDR=LOCALHOST_PEER,
            HTTP_CF_CONNECTING_IP="9.9.9.9",
            HTTP_X_FORWARDED_FOR="198.51.100.9",
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, "198.51.100.9")

    def test_cloudflare_peer_still_prioritized_correctly(self):
        request = factory.get(
            "/",
            REMOTE_ADDR=CLOUDFLARE_PEER,
            HTTP_CF_CONNECTING_IP="198.51.100.9",
            HTTP_X_FORWARDED_FOR="1.2.3.4",
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, "198.51.100.9")

    def test_untrusted_peer_still_ignored(self):
        request = factory.get(
            "/", REMOTE_ADDR=NON_TRUSTED_PEER, HTTP_X_FORWARDED_FOR="9.9.9.9"
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, NON_TRUSTED_PEER)


class DefaultFlagBehaviorTests(TestCase):
    """trust_cloudflare_only unset (None sentinel) -> follows `not DEBUG`."""

    def setUp(self):
        self.cf_patcher = patch(
            f"{MODULE}.CLOUDFLARE_IP_RANGES", TEST_CLOUDFLARE_RANGES
        )
        self.cf_patcher.start()
        self.addCleanup(self.cf_patcher.stop)

    def test_debug_true_defaults_to_trusting_localhost(self):
        with patch(
            f"{MODULE}.auth_config.trust_cloudflare_only", None
        ), override_settings(DEBUG=True):
            middleware = IPAddressMiddleware(_get_response)
        self.assertGreater(len(middleware.localhost_networks), 0)

    def test_debug_false_defaults_to_cloudflare_only(self):
        with patch(
            f"{MODULE}.auth_config.trust_cloudflare_only", None
        ), override_settings(DEBUG=False):
            middleware = IPAddressMiddleware(_get_response)
        self.assertEqual(len(middleware.localhost_networks), 0)

    def test_explicit_setting_overrides_debug_default(self):
        with override_settings(DEBUG=True), patch(
            f"{MODULE}.auth_config.trust_cloudflare_only", True
        ):
            middleware = IPAddressMiddleware(_get_response)
        self.assertEqual(len(middleware.localhost_networks), 0)

    def test_explicit_false_overrides_debug_default_too(self):
        """Explicit False must win even when DEBUG=True would otherwise trust localhost."""
        with override_settings(DEBUG=True), patch(
            f"{MODULE}.auth_config.trust_cloudflare_only", False
        ):
            middleware = IPAddressMiddleware(_get_response)
        self.assertGreater(len(middleware.localhost_networks), 0)
        # NOTE: False explicitly means "also trust localhost" — same
        # as the DEBUG=True default in this case, so this test mainly
        # guards against a future regression where False gets treated
        # as falsy/missing and silently coerced to the DEBUG default
        # by coincidence rather than by explicit value.


class ParsingRobustnessTests(TestCase):
    def setUp(self):
        self.cf_patcher = patch(
            f"{MODULE}.CLOUDFLARE_IP_RANGES", TEST_CLOUDFLARE_RANGES
        )
        self.cf_patcher.start()
        self.addCleanup(self.cf_patcher.stop)

        self.trust_patcher = patch(f"{MODULE}.auth_config.trust_cloudflare_only", False)
        self.trust_patcher.start()
        self.addCleanup(self.trust_patcher.stop)

        self.middleware = IPAddressMiddleware(_get_response)

    def test_skips_trailing_garbage_in_forwarded_for(self):
        request = factory.get(
            "/",
            REMOTE_ADDR=LOCALHOST_PEER,
            HTTP_X_FORWARDED_FOR="198.51.100.9, not-an-ip",
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, "198.51.100.9")

    def test_empty_forwarded_for_falls_back_to_remote_addr(self):
        request = factory.get("/", REMOTE_ADDR=LOCALHOST_PEER, HTTP_X_FORWARDED_FOR="")
        self.middleware(request)
        self.assertEqual(request.ip_address, LOCALHOST_PEER)

    def test_all_garbage_forwarded_for_falls_back_to_remote_addr(self):
        request = factory.get(
            "/",
            REMOTE_ADDR=LOCALHOST_PEER,
            HTTP_X_FORWARDED_FOR="garbage, more-garbage",
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, LOCALHOST_PEER)

    def test_supports_ipv6_in_forwarded_header(self):
        request = factory.get(
            "/", REMOTE_ADDR=LOCALHOST_PEER, HTTP_X_FORWARDED_FOR="2001:db8::1"
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, "2001:db8::1")

    def test_whitespace_trimmed_from_entries(self):
        request = factory.get(
            "/",
            REMOTE_ADDR=LOCALHOST_PEER,
            HTTP_X_FORWARDED_FOR="1.2.3.4,   198.51.100.9   ",
        )
        self.middleware(request)
        self.assertEqual(request.ip_address, "198.51.100.9")

    def test_returns_none_when_nothing_valid_anywhere(self):
        request = factory.get("/")
        request.META.pop("REMOTE_ADDR", None)
        self.middleware(request)
        self.assertIsNone(request.ip_address)


class ConfigValidationTests(TestCase):
    def test_raises_when_cloudflare_ranges_empty(self):
        with patch(f"{MODULE}.CLOUDFLARE_IP_RANGES", []):
            with self.assertRaises(ImproperlyConfigured):
                IPAddressMiddleware(_get_response)

    def test_raises_when_all_ranges_malformed(self):
        with patch(f"{MODULE}.CLOUDFLARE_IP_RANGES", ["not-a-cidr", "also-garbage"]):
            with self.assertRaises(ImproperlyConfigured):
                IPAddressMiddleware(_get_response)
