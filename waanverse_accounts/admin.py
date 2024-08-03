from django.contrib import admin
from .models import EmailConfirmationCode, UserLoginActivity, ResetPasswordCode


admin.site.register(EmailConfirmationCode)
admin.site.register(UserLoginActivity)
admin.site.register(ResetPasswordCode)
