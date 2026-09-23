# tests/test_login_throttling.py
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.throttling import SimpleRateThrottle
from tests.utils import generate_rsa_keypair_files
from unittest.mock import patch
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache
from dj_waanverse_auth.throttles import LoginIPThrottle, LoginIdentifierThrottle
from dj_waanverse_auth.views.login_views import LoginView

import tempfile
from pathlib import Path

Account = get_user_model()

VIEW_MODULE = "dj_waanverse_auth.views.login_views"
KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"


class LoginThrottlingTests(APITestCase):
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

        # Ensure the login view actually uses these throttle classes,
        # regardless of what's wired up via settings.
        self._view_throttles_patcher = patch.object(
            LoginView,
            "throttle_classes",
            [LoginIPThrottle, LoginIdentifierThrottle],
        )
        self._view_throttles_patcher.start()
        self.addCleanup(self._view_throttles_patcher.stop)

        # Patch rates directly on the class attribute so they take
        # effect regardless of when DEFAULT_THROTTLE_RATES was read
        # from settings at import time.
        self._throttle_rates_patcher = patch.object(
            SimpleRateThrottle,
            "THROTTLE_RATES",
            {
                **SimpleRateThrottle.THROTTLE_RATES,
                "login-ip": "2/min",
                "login-identifier": "2/min",
            },
        )
        self._throttle_rates_patcher.start()
        self.addCleanup(self._throttle_rates_patcher.stop)

        cache.clear()
        self.url = reverse("dj_waanverse_auth_login")
        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
            is_active=True,
        )

    def tearDown(self):
        for p in self.patchers:
            p.stop()

    def test_ip_throttle_blocks_after_rate_exceeded(self):
        for _ in range(2):
            response = self.client.post(
                self.url,
                {"identifier": "wave@example.com", "password": "wrong"},
                content_type="application/json",
                REMOTE_ADDR="203.0.113.5",
            )
            self.assertNotEqual(response.status_code, 429)

        response = self.client.post(
            self.url,
            {"identifier": "wave@example.com", "password": "wrong"},
            content_type="application/json",
            REMOTE_ADDR="203.0.113.5",
        )
        self.assertEqual(response.status_code, 429)

    def test_identifier_throttle_triggers_across_rotating_ips(self):
        for i in range(2):
            self.client.post(
                self.url,
                {"identifier": "wave@example.com", "password": "wrong"},
                content_type="application/json",
                REMOTE_ADDR=f"203.0.113.{i + 1}",
            )

        response = self.client.post(
            self.url,
            {"identifier": "wave@example.com", "password": "wrong"},
            content_type="application/json",
            REMOTE_ADDR="203.0.113.99",
        )
        self.assertEqual(response.status_code, 429)

    def test_correct_credentials_still_count_toward_the_limit(self):
        """
        A successful login attempt consumes throttle quota too — an
        attacker shouldn't be able to distinguish "throttled" from
        "not yet throttled" based on whether guesses happen to be
        wrong vs. right.
        """
        self.client.post(
            self.url,
            {"identifier": "wave@example.com", "password": "StrongPassword123!"},
            content_type="application/json",
            REMOTE_ADDR="203.0.113.5",
        )
        self.client.post(
            self.url,
            {"identifier": "wave@example.com", "password": "wrong"},
            content_type="application/json",
            REMOTE_ADDR="203.0.113.5",
        )
        response = self.client.post(
            self.url,
            {"identifier": "wave@example.com", "password": "wrong"},
            content_type="application/json",
            REMOTE_ADDR="203.0.113.5",
        )
        self.assertEqual(response.status_code, 429)
