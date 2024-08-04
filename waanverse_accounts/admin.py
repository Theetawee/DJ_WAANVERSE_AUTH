from django.contrib import admin
from .models import (
    EmailConfirmationCode,
    UserLoginActivity,
    ResetPasswordCode,
    EmailAddress,
)
from django.conf import settings


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

else:

    admin.site.register(EmailConfirmationCode)
    admin.site.register(UserLoginActivity)
    admin.site.register(ResetPasswordCode)
    admin.site.register(EmailAddress)
