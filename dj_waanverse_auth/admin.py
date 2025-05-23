from dj_waanverse_auth.config.settings import auth_config

if auth_config.enable_admin:
    from django.contrib import admin

    from .models import (
        GoogleStateToken,
        MultiFactorAuth,
        ResetPasswordToken,
        UserSession,
        VerificationCode,
    )

    @admin.register(UserSession)
    class UserSessionAdmin(admin.ModelAdmin):
        list_display = (
            "id",
            "account",
            "last_used",
            "is_active",
        )
        list_filter = ("is_active", "created_at")
        search_fields = ("account__email", "user_agent", "ip_address")
        ordering = ("-last_used",)

    admin.site.register(MultiFactorAuth)
    admin.site.register(VerificationCode)
    admin.site.register(ResetPasswordToken)
    admin.site.register(GoogleStateToken)
