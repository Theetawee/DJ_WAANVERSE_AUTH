# dj_waanverse_auth/admin.py
from dj_waanverse_auth.config.settings import auth_config

if auth_config.enable_admin:
    from django.contrib import admin

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

    @admin.register(Session)
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
            updated = 0
            for session in queryset.filter(is_revoked=False):
                session.revoke()
                updated += 1
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

    @admin.register(VerificationCode)
    class VerificationCodeAdmin(_CodeAdminBase):
        pass

    @admin.register(PasswordResetCode)
    class PasswordResetCodeAdmin(_CodeAdminBase):
        pass
