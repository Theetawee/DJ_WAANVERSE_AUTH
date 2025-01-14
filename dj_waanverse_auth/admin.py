from dj_waanverse_auth.settings.settings import auth_config

if auth_config.enable_admin:
    from django.contrib import admin

    from .models import (
        MultiFactorAuth,
        ResetPasswordToken,
        UserSession,
        VerificationCode,
    )

    # if auth_config.USE_UNFOLD:
    #     from unfold.admin import ModelAdmin
    #     @admin.register(EmailConfirmationCode)
    #     class EmailConfirmationCodeAdminClass(ModelAdmin):
    #         pass
    #     @admin.register(UserLoginActivity)
    #     class UserLoginActivityAdminClass(ModelAdmin):
    #         pass
    #     @admin.register(ResetPasswordCode)
    #     class ResetPasswordCodeAdminClass(ModelAdmin):
    #         pass
    #     @admin.register(EmailAddress)
    #     class EmailAddressAdminClass(ModelAdmin):
    #         pass
    #     @admin.register(MultiFactorAuth)
    #     class MultiFactorAuthAdminClass(ModelAdmin):
    #         pass
    # else:

    admin.site.register(MultiFactorAuth)
    admin.site.register(VerificationCode)
    admin.site.register(UserSession)
    admin.site.register(ResetPasswordToken)
