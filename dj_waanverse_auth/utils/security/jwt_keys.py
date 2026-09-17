from __future__ import annotations

import functools

from django.core.exceptions import ImproperlyConfigured

from dj_waanverse_auth import settings as auth_config


@functools.lru_cache(maxsize=1)
def get_private_key() -> str:
    path = getattr(auth_config, "private_key_path", None)
    if not path:
        raise ImproperlyConfigured(
            "PRIVATE_KEY_PATH must be set in WAANVERSE_AUTH_CONFIG to issue tokens."
        )
    with open(path, "r") as f:
        return f.read()


@functools.lru_cache(maxsize=1)
def get_public_key() -> str:
    path = getattr(auth_config, "public_key_path", None)
    if not path:
        raise ImproperlyConfigured(
            "PUBLIC_KEY_PATH must be set in WAANVERSE_AUTH_CONFIG to verify tokens."
        )
    with open(path, "r") as f:
        return f.read()


def clear_key_cache() -> None:
    """Call after swapping key files under override_settings in tests."""
    get_private_key.cache_clear()
    get_public_key.cache_clear()
