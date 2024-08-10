from django.conf import settings
from django.contrib import admin

from .models import (EmailAddress, EmailConfirmationCode, MultiFactorAuth,
                     ResetPasswordCode, UserLoginActivity)

if "unfold" in settings.INSTALLED_APPS:
    from unfold.admin import ModelAdmin

    @admin.register(EmailConfirmationCode)
    class EmailConfirmationCodeAdminClass(ModelAdmin):
        pass

    @admin.register(UserLoginActivity)
    class UserLoginActivityAdminClass(ModelAdmin):
        pass

    @admin.register(ResetPasswordCode)
    class ResetPasswordCodeAdminClass(ModelAdmin):
        pass

    @admin.register(EmailAddress)
    class EmailAddressAdminClass(ModelAdmin):
        pass

    @admin.register(MultiFactorAuth)
    class MultiFactorAuthAdminClass(ModelAdmin):
        pass

else:

    admin.site.register(EmailConfirmationCode)
    admin.site.register(UserLoginActivity)
    admin.site.register(ResetPasswordCode)
    admin.site.register(EmailAddress)
    admin.site.register(MultiFactorAuth)
