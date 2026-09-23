# dj_waanverse_auth/admin.py
from __future__ import annotations

from django.contrib import admin
from django.utils import timezone

from dj_waanverse_auth.config.settings import auth_config
from dj_waanverse_auth.models import PasswordResetCode, Session, VerificationCode


class NoAddAdminMixin:
    """
    These records are only ever created by the application itself
    (login/signup/verification flows) and carry hashed secrets —
    there's nothing meaningful for an admin to create by hand.
    Mutation happens only through the actions below, never a raw
    add/edit form.
    """

    def has_add_permission(self, request):
        return False


class SessionAdmin(NoAddAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "account",
        "ip_address",
        "user_agent_short",
        "created_at",
        "last_used_at",
        "is_revoked",
    )
    list_filter = ("is_revoked", "created_at")
    search_fields = ("account__email_address", "ip_address")
    ordering = ("-last_used_at",)
    readonly_fields = (
        "id",
        "account",
        "refresh_token_hash",
        "user_agent",
        "ip_address",
        "created_at",
        "last_used_at",
        "revoked_at",
    )
    actions = ["revoke_sessions"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("account")

    def user_agent_short(self, obj):
        if len(obj.user_agent) > 60:
            return f"{obj.user_agent[:60]}…"
        return obj.user_agent

    user_agent_short.short_description = "User agent"

    def revoke_sessions(self, request, queryset):
        # Bulk update rather than a per-instance loop calling
        # .revoke() — same pattern already used in
        # RevokeOtherSessionsView, and avoids N+1 writes here.
        updated = queryset.filter(is_revoked=False).update(
            is_revoked=True, revoked_at=timezone.now()
        )
        self.message_user(request, f"Revoked {updated} session(s).")

    revoke_sessions.short_description = "Revoke selected sessions"


class _CodeAdminBase(NoAddAdminMixin, admin.ModelAdmin):
    list_display = (
        "account",
        "created_at",
        "code_expires_at",
        "link_expires_at",
        "attempts",
        "is_used",
    )
    list_filter = ("is_used", "created_at")
    search_fields = ("account__email_address",)
    ordering = ("-created_at",)
    readonly_fields = (
        "account",
        "code_hash",
        "token_hash",
        "created_at",
        "code_expires_at",
        "link_expires_at",
        "attempts",
        "is_used",
    )
    actions = ["invalidate_codes"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("account")

    def invalidate_codes(self, request, queryset):
        updated = queryset.filter(is_used=False).update(is_used=True)
        self.message_user(request, f"Invalidated {updated} code(s).")

    invalidate_codes.short_description = "Mark selected codes as used"


class VerificationCodeAdmin(_CodeAdminBase):
    pass


class PasswordResetCodeAdmin(_CodeAdminBase):
    pass


def register_admin() -> None:
    """
    Registers dj_waanverse_auth's admin classes, gated by
    ENABLE_ADMIN in WAANVERSE_AUTH_CONFIG. Kept as a standalone
    function (rather than bare register() calls at module level) so
    tests can call it directly under a patched setting without
    needing to reload this whole module.
    """

    if not auth_config.enable_admin:
        return

    for model, admin_class in (
        (Session, SessionAdmin),
        (VerificationCode, VerificationCodeAdmin),
        (PasswordResetCode, PasswordResetCodeAdmin),
    ):
        if model not in admin.site._registry:
            admin.site.register(model, admin_class)


register_admin()
