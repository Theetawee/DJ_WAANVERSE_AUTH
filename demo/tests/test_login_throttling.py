# tests/test_login_throttling.py
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from tests.utils import generate_rsa_keypair_files
from unittest.mock import patch
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache

import tempfile
from pathlib import Path

Account = get_user_model()


VIEW_MODULE = "dj_waanverse_auth.views.login_views"
KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"


@override_settings(
    DEBUG=True,
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_RATES": {"login-ip": "2/min", "login-identifier": "2/min"},
    },
)
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

        cache.clear()
        self.url = reverse("dj_waanverse_auth_login")
        self.account = Account.objects.create_user(
            email_address="wave@example.com",
            password="StrongPassword123!",
            is_active=True,
        )

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
