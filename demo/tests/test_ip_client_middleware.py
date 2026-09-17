"""
Tests for dj_waanverse_auth.middleware.IPAddressMiddleware

Assumes this file lives inside your Django app's test suite (e.g.
dj_waanverse_auth/tests/test_middleware.py) where Django settings are
already configured. Run with `manage.py test` or `pytest --ds=...`.

Design notes:
- CLOUDFLARE_IP_RANGES is patched to a small, deterministic test range
  (TEST-NET-3, 203.0.113.0/24, and a documentation-only IPv6 block)
  rather than relying on the real published Cloudflare ranges. This
  keeps the tests independent of that list ever changing.
- trust_cloudflare_only is patched per-test on the auth_config module,
  since the middleware reads it once at __init__ time.
- REMOTE_ADDR / X-Forwarded-For / CF-Connecting-IP are all set directly
  via RequestFactory's META kwargs to make each scenario explicit.
"""

from __future__ import annotations
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from dj_waanverse_auth.middleware import client_ip as middleware_module
from dj_waanverse_auth.middleware import IPAddressMiddleware

# Deterministic test-only "Cloudflare" ranges (RFC 5737 / RFC 3849 blocks,
# never routable, safe to hardcode in tests).
TEST_CF_RANGES = ["203.0.113.0/24", "2001:db8:cf::/48"]

CF_PEER_V4 = "203.0.113.5"
CF_PEER_V6 = "2001:db8:cf::1"
LOCAL_PEER_V4 = "127.0.0.1"
LOCAL_PEER_V6 = "::1"
UNTRUSTED_PEER = "198.51.100.9"  # RFC 5737 TEST-NET-2, outside all trusted ranges


def make_response(request):
    return HttpResponse("ok")


class MiddlewareTestBase(TestCase):
    """Shared helpers for constructing a middleware instance under test."""

    def setUp(self):
        self.factory = RequestFactory()

    def build_middleware(self, cloudflare_only, cf_ranges=None):
        """
        Builds an IPAddressMiddleware instance with CLOUDFLARE_IP_RANGES
        and trust_cloudflare_only patched to controlled test values.
        """
        cf_ranges = TEST_CF_RANGES if cf_ranges is None else cf_ranges
        patch_ranges = mock.patch.object(
            middleware_module, "CLOUDFLARE_IP_RANGES", cf_ranges
        )
        patch_flag = mock.patch.object(
            middleware_module.auth_config, "trust_cloudflare_only", cloudflare_only
        )
        patch_ranges.start()
        patch_flag.start()
        self.addCleanup(patch_ranges.stop)
        self.addCleanup(patch_flag.stop)
        return IPAddressMiddleware(make_response)

    def make_request(self, **meta):
        request = self.factory.get("/")
        # RequestFactory seeds REMOTE_ADDR itself; let callers override
        # or clear it explicitly via meta.
        request.META.update(meta)
        return request


class InitializationTests(MiddlewareTestBase):
    def test_raises_if_no_valid_cloudflare_ranges_configured(self):
        with self.assertRaises(ImproperlyConfigured):
            self.build_middleware(cloudflare_only=False, cf_ranges=[])

    def test_raises_if_all_cloudflare_ranges_are_malformed(self):
        with self.assertRaises(ImproperlyConfigured):
            self.build_middleware(
                cloudflare_only=False, cf_ranges=["not-a-cidr", "999.999.0.0/33"]
            )

    def test_malformed_entries_are_skipped_but_valid_ones_kept(self):
        mw = self.build_middleware(
            cloudflare_only=False,
            cf_ranges=["not-a-cidr", *TEST_CF_RANGES],
        )
        self.assertEqual(len(mw.cloudflare_networks), 2)

    def test_localhost_networks_populated_when_not_cloudflare_only(self):
        mw = self.build_middleware(cloudflare_only=False)
        self.assertTrue(len(mw.localhost_networks) > 0)

    def test_localhost_networks_empty_when_cloudflare_only(self):
        mw = self.build_middleware(cloudflare_only=True)
        self.assertEqual(mw.localhost_networks, ())


class CloudflarePeerTests(MiddlewareTestBase):
    """Requests whose REMOTE_ADDR is inside the trusted Cloudflare ranges."""

    def setUp(self):
        super().setUp()
        self.mw = self.build_middleware(cloudflare_only=False)

    def test_uses_cf_connecting_ip_when_present(self):
        request = self.make_request(
            REMOTE_ADDR=CF_PEER_V4,
            HTTP_CF_CONNECTING_IP="9.9.9.9",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, "9.9.9.9")

    def test_cf_connecting_ip_whitespace_is_stripped(self):
        request = self.make_request(
            REMOTE_ADDR=CF_PEER_V4,
            HTTP_CF_CONNECTING_IP="  9.9.9.9  ",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, "9.9.9.9")

    def test_falls_back_to_last_xff_when_cf_header_absent(self):
        request = self.make_request(
            REMOTE_ADDR=CF_PEER_V4,
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2, 3.3.3.3",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, "3.3.3.3")

    def test_falls_back_to_last_xff_when_cf_header_invalid(self):
        request = self.make_request(
            REMOTE_ADDR=CF_PEER_V4,
            HTTP_CF_CONNECTING_IP="not-an-ip",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, "2.2.2.2")

    def test_falls_back_to_last_xff_when_cf_header_empty_string(self):
        request = self.make_request(
            REMOTE_ADDR=CF_PEER_V4,
            HTTP_CF_CONNECTING_IP="",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, "2.2.2.2")

    def test_falls_back_to_remote_addr_when_no_headers_present(self):
        request = self.make_request(REMOTE_ADDR=CF_PEER_V4)
        self.mw(request)
        self.assertEqual(request.ip_address, CF_PEER_V4)

    def test_xff_skips_trailing_malformed_entries(self):
        request = self.make_request(
            REMOTE_ADDR=CF_PEER_V4,
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2, garbage, ",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, "2.2.2.2")

    def test_xff_all_entries_invalid_falls_back_to_remote_addr(self):
        request = self.make_request(
            REMOTE_ADDR=CF_PEER_V4,
            HTTP_X_FORWARDED_FOR="garbage, also-garbage",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, CF_PEER_V4)

    def test_ipv6_cloudflare_peer_and_cf_header(self):
        request = self.make_request(
            REMOTE_ADDR=CF_PEER_V6,
            HTTP_CF_CONNECTING_IP="2001:db8::abcd",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, "2001:db8::abcd")

    def test_xff_single_entry(self):
        request = self.make_request(
            REMOTE_ADDR=CF_PEER_V4,
            HTTP_X_FORWARDED_FOR="5.5.5.5",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, "5.5.5.5")

    def test_xff_entry_with_port_like_suffix_is_rejected(self):
        # "1.2.3.4:8080" does not parse as a bare IP address, so it
        # should be skipped as junk, falling through to the prior entry.
        request = self.make_request(
            REMOTE_ADDR=CF_PEER_V4,
            HTTP_X_FORWARDED_FOR="1.1.1.1, 1.2.3.4:8080",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, "1.1.1.1")


class LocalhostPeerTrustedTests(MiddlewareTestBase):
    """Requests from localhost when cloudflare_only=False (dev-style config)."""

    def setUp(self):
        super().setUp()
        self.mw = self.build_middleware(cloudflare_only=False)

    def test_uses_last_xff_entry_ipv4(self):
        request = self.make_request(
            REMOTE_ADDR=LOCAL_PEER_V4,
            HTTP_X_FORWARDED_FOR="8.8.8.8, 4.4.4.4",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, "4.4.4.4")

    def test_uses_last_xff_entry_ipv6_peer(self):
        request = self.make_request(
            REMOTE_ADDR=LOCAL_PEER_V6,
            HTTP_X_FORWARDED_FOR="8.8.8.8, 4.4.4.4",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, "4.4.4.4")

    def test_cf_connecting_ip_header_is_ignored_for_non_cf_peer(self):
        # Only the Cloudflare-peer branch consults CF-Connecting-IP.
        request = self.make_request(
            REMOTE_ADDR=LOCAL_PEER_V4,
            HTTP_CF_CONNECTING_IP="9.9.9.9",
            HTTP_X_FORWARDED_FOR="4.4.4.4",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, "4.4.4.4")

    def test_falls_back_to_remote_addr_when_no_xff(self):
        request = self.make_request(REMOTE_ADDR=LOCAL_PEER_V4)
        self.mw(request)
        self.assertEqual(request.ip_address, LOCAL_PEER_V4)

    def test_xff_all_invalid_falls_back_to_remote_addr(self):
        request = self.make_request(
            REMOTE_ADDR=LOCAL_PEER_V4,
            HTTP_X_FORWARDED_FOR="nope, still-nope",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, LOCAL_PEER_V4)


class LocalhostPeerUntrustedWhenCloudflareOnlyTests(MiddlewareTestBase):
    """When trust_cloudflare_only=True, localhost must NOT be trusted."""

    def setUp(self):
        super().setUp()
        self.mw = self.build_middleware(cloudflare_only=True)

    def test_xff_ignored_for_localhost_peer(self):
        request = self.make_request(
            REMOTE_ADDR=LOCAL_PEER_V4,
            HTTP_X_FORWARDED_FOR="4.4.4.4",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, LOCAL_PEER_V4)

    def test_cloudflare_peer_still_trusted(self):
        # cloudflare_only only removes the localhost carve-out; the
        # Cloudflare branch itself is unaffected.
        request = self.make_request(
            REMOTE_ADDR=CF_PEER_V4,
            HTTP_CF_CONNECTING_IP="9.9.9.9",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, "9.9.9.9")


class UntrustedPeerTests(MiddlewareTestBase):
    """Requests from a peer that is neither Cloudflare nor a trusted local proxy."""

    def setUp(self):
        super().setUp()
        self.mw = self.build_middleware(cloudflare_only=False)

    def test_headers_are_ignored_uses_remote_addr(self):
        request = self.make_request(
            REMOTE_ADDR=UNTRUSTED_PEER,
            HTTP_CF_CONNECTING_IP="9.9.9.9",
            HTTP_X_FORWARDED_FOR="4.4.4.4",
        )
        self.mw(request)
        self.assertEqual(request.ip_address, UNTRUSTED_PEER)

    def test_headers_ignored_even_with_cloudflare_only(self):
        mw = self.build_middleware(cloudflare_only=True)
        request = self.make_request(
            REMOTE_ADDR=UNTRUSTED_PEER,
            HTTP_X_FORWARDED_FOR="4.4.4.4",
        )
        mw(request)
        self.assertEqual(request.ip_address, UNTRUSTED_PEER)


class EdgeCaseTests(MiddlewareTestBase):
    def setUp(self):
        super().setUp()
        self.mw = self.build_middleware(cloudflare_only=False)

    def test_missing_remote_addr_and_no_trusted_headers_gives_none(self):
        request = self.make_request()
        del request.META["REMOTE_ADDR"]
        self.mw(request)
        self.assertIsNone(request.ip_address)

    def test_invalid_remote_addr_gives_none(self):
        request = self.make_request(REMOTE_ADDR="not-an-ip-at-all")
        self.mw(request)
        self.assertIsNone(request.ip_address)

    def test_empty_string_remote_addr_gives_none(self):
        request = self.make_request(REMOTE_ADDR="")
        self.mw(request)
        self.assertIsNone(request.ip_address)

    def test_remote_addr_with_whitespace_is_stripped(self):
        request = self.make_request(REMOTE_ADDR=f"  {UNTRUSTED_PEER}  ")
        self.mw(request)
        self.assertEqual(request.ip_address, UNTRUSTED_PEER)

    def test_response_is_passed_through_unchanged(self):
        request = self.make_request(REMOTE_ADDR=UNTRUSTED_PEER)
        response = self.mw(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_ip_address_attribute_always_set(self):
        # Even in the total-failure case, the attribute exists (as None)
        # rather than being left unset, so downstream code can rely on
        # getattr(request, "ip_address", None) safely — or just direct
        # access after this middleware runs.
        request = self.make_request()
        del request.META["REMOTE_ADDR"]
        self.mw(request)
        self.assertTrue(hasattr(request, "ip_address"))
        self.assertIsNone(request.ip_address)
