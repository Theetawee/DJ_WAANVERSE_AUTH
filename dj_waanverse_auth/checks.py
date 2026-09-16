"""
System checks that validate the WAANVERSE_AUTH_CONFIG settings are
internally consistent. Runs automatically on manage.py check,
runserver, migrate, and test — see apps.py for registration.
"""

from __future__ import annotations

from django.core.checks import Error, register

from dj_waanverse_auth.config.settings import auth_config as settings


@register()
def check_turnstile_config(app_configs, **kwargs):
    """
    ENABLE_TURNSTILE requires a secret key — without one, every
    signup would fail closed at request time instead of at startup.
    """

    errors = []

    if settings.turnstile_enabled and not settings.turnstile_secret_key:
        errors.append(
            Error(
                "ENABLE_TURNSTILE is True but TURNSTILE_SECRET_KEY is not set.",
                hint=(
                    "Set WAANVERSE_AUTH_CONFIG['TURNSTILE_SECRET_KEY'], or "
                    "disable Turnstile with ENABLE_TURNSTILE = False."
                ),
                id="dj_waanverse_auth.E001",
            )
        )

    return errors


@register()
def check_authentication_identifiers(app_configs, **kwargs):
    """
    At least one identifier type must be enabled, and every entry
    must be one this package actually knows how to handle.
    """

    errors = []
    valid_identifiers = {"email", "phone"}
    configured = set(settings.authentication_identifiers or [])

    if not configured:
        errors.append(
            Error(
                "AUTHENTICATION_IDENTIFIERS is empty — no signup method "
                "would be reachable.",
                hint="Enable at least one of: email, phone.",
                id="dj_waanverse_auth.E002",
            )
        )

    unknown = configured - valid_identifiers
    if unknown:
        errors.append(
            Error(
                f"AUTHENTICATION_IDENTIFIERS contains unknown value(s): "
                f"{sorted(unknown)}.",
                hint=f"Valid options are: {sorted(valid_identifiers)}.",
                id="dj_waanverse_auth.E003",
            )
        )

    return errors
