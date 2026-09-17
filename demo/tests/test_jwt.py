import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from tests.utils import tamper_jwt_signature

import jwt as pyjwt
from django.test import TestCase

from dj_waanverse_auth.utils.security.jwt import (
    ACCESS,
    REFRESH,
    TokenError,
    decode_token,
    encode_token,
)
from dj_waanverse_auth.utils.security.jwt_keys import clear_key_cache, get_private_key
from tests.utils import generate_rsa_keypair_files

KEYS_MODULE = "dj_waanverse_auth.utils.security.jwt_keys.auth_config"
JWT_MODULE = "dj_waanverse_auth.utils.security.jwt.auth_config"


class JWTTests(TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.private_path, self.public_path = generate_rsa_keypair_files(
            Path(self._tmp.name)
        )

        self._other_tmp = tempfile.TemporaryDirectory()
        self.other_private_path, _ = generate_rsa_keypair_files(
            Path(self._other_tmp.name)
        )

        self.patchers = [
            patch(f"{KEYS_MODULE}.private_key_path", self.private_path),
            patch(f"{KEYS_MODULE}.public_key_path", self.public_path),
        ]
        for p in self.patchers:
            p.start()
        clear_key_cache()

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        clear_key_cache()
        self._tmp.cleanup()
        self._other_tmp.cleanup()

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_encode_decode_access_roundtrip(self):
        token, jti, _ = encode_token(
            account_id=42,
            session_id="s1",
            token_type=ACCESS,
            lifetime=timedelta(minutes=5),
        )
        payload = decode_token(token, expected_type=ACCESS)

        self.assertEqual(payload["sub"], "42")
        self.assertEqual(payload["sid"], "s1")
        self.assertEqual(payload["type"], ACCESS)
        self.assertEqual(payload["jti"], jti)

    def test_encode_decode_refresh_roundtrip(self):
        token, _, _ = encode_token(
            account_id=42,
            session_id="s1",
            token_type=REFRESH,
            lifetime=timedelta(days=1),
        )
        payload = decode_token(token, expected_type=REFRESH)
        self.assertEqual(payload["type"], REFRESH)

    # ------------------------------------------------------------------
    # Type confusion
    # ------------------------------------------------------------------

    def test_refresh_token_rejected_as_access_token(self):
        token, _, _ = encode_token(
            account_id=1,
            session_id="s1",
            token_type=REFRESH,
            lifetime=timedelta(days=1),
        )
        with self.assertRaises(TokenError):
            decode_token(token, expected_type=ACCESS)

    def test_access_token_rejected_as_refresh_token(self):
        token, _, _ = encode_token(
            account_id=1,
            session_id="s1",
            token_type=ACCESS,
            lifetime=timedelta(minutes=5),
        )
        with self.assertRaises(TokenError):
            decode_token(token, expected_type=REFRESH)

    # ------------------------------------------------------------------
    # Expiry
    # ------------------------------------------------------------------

    def test_expired_token_rejected(self):
        token, _, _ = encode_token(
            account_id=1,
            session_id="s1",
            token_type=ACCESS,
            lifetime=timedelta(seconds=-1),
        )
        with self.assertRaises(TokenError):
            decode_token(token, expected_type=ACCESS)

    # ------------------------------------------------------------------
    # Tampering / forgery
    # ------------------------------------------------------------------

    def test_tampered_signature_rejected(self):
        token, _, _ = encode_token(
            account_id=1,
            session_id="s1",
            token_type=ACCESS,
            lifetime=timedelta(minutes=5),
        )
        with self.assertRaises(TokenError):
            decode_token(tamper_jwt_signature(token), expected_type=ACCESS)

    def test_token_signed_with_different_keypair_rejected(self):
        with patch(f"{KEYS_MODULE}.private_key_path", self.other_private_path):
            clear_key_cache()
            forged_token, _, _ = encode_token(
                account_id=1,
                session_id="s1",
                token_type=ACCESS,
                lifetime=timedelta(minutes=5),
            )
        clear_key_cache()  # back to the real keypair for decode

        with self.assertRaises(TokenError):
            decode_token(forged_token, expected_type=ACCESS)

    def test_alg_none_forged_token_rejected(self):
        forged = pyjwt.encode(
            {
                "sub": "1",
                "sid": "s1",
                "type": ACCESS,
                "jti": "x",
                "iat": 0,
                "exp": 9999999999,
                "iss": "dj_waanverse_auth",
            },
            key="",
            algorithm="none",
        )
        with self.assertRaises(TokenError):
            decode_token(forged, expected_type=ACCESS)

    # ------------------------------------------------------------------
    # Issuer and required claims
    # ------------------------------------------------------------------

    def test_wrong_issuer_rejected(self):
        with patch(f"{JWT_MODULE}.jwt_issuer", "issuer-a"):
            token, _, _ = encode_token(
                account_id=1,
                session_id="s1",
                token_type=ACCESS,
                lifetime=timedelta(minutes=5),
            )
        with patch(f"{JWT_MODULE}.jwt_issuer", "issuer-b"):
            with self.assertRaises(TokenError):
                decode_token(token, expected_type=ACCESS)

    def test_missing_required_claim_rejected(self):
        incomplete = pyjwt.encode(
            {
                "sub": "1",
                "type": ACCESS,
                "jti": "x",
                "iat": 0,
                "exp": 9999999999,
                "iss": "dj_waanverse_auth",
            },
            get_private_key(),
            algorithm="RS256",
        )  # "sid" deliberately omitted
        with self.assertRaises(TokenError):
            decode_token(incomplete, expected_type=ACCESS)
