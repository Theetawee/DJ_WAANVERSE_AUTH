from django.contrib import admin
from .models import Account, EmailConfirmationCode, UserLoginActivity, ResetPasswordCode
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin
from django.contrib.auth.models import Group
from unfold.forms import UserCreationForm, AdminPasswordChangeForm, UserChangeForm

admin.site.unregister(Group)


class AccountAdmin(UserAdmin, ModelAdmin):
    # Define the fields to be displayed in the list view
    add_form = UserCreationForm
    form = UserChangeForm
    change_password_form = AdminPasswordChangeForm
    list_display = (
        "email",
        "is_active",
        "is_staff",
        "name",
        "username",
        "last_login",
        "date_joined",
    )

    # Define fields to be searchable
    search_fields = ("email", "name", "username")

    # Define fields that should be read-only
    readonly_fields = ("last_login", "date_joined")

    # Define how the fields should be grouped on the edit page
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "name",
                    "username",
                    "date_of_birth",
                    "pronouns",
                    "phone",
                    "profile_image",
                    "custom_pronouns",
                )
            },
        ),
        (
            "Account security",
            {"fields": ("mfa_activated", "mfa_secret", "recovery_codes")},
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # Define which fields to include in filter options
    list_filter = ("is_active", "is_staff", "is_superuser", "date_of_birth", "pronouns")

    # Specify filters and additional options for the admin interface
    filter_horizontal = ()

    # Include user creation and change forms
    add_fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "username",
                    "name",
                    "password1",
                    "password2",
                    "date_of_birth",
                    "pronouns",
                    "phone",
                    "profile_image",
                )
            },
        ),
    )

    # Ensure `USER_ADMIN` correctly handles permissions
    def get_fieldsets(self, request, obj=None):
        if obj:
            return super().get_fieldsets(request, obj)
        return (
            (None, {"fields": ("email", "password1", "password2")}),
            (
                "Personal info",
                {
                    "fields": (
                        "name",
                        "username",
                        "date_of_birth",
                        "pronouns",
                        "phone",
                        "profile_image",
                    )
                },
            ),
        )


admin.site.register(Account, AccountAdmin)


class EmailConfirmationCodeAdmin(ModelAdmin):
    model = EmailConfirmationCode


@admin.register(EmailConfirmationCode)
class EmailConfirmationCode(ModelAdmin):
    pass


@admin.register(UserLoginActivity)
class UserLoginActivity(ModelAdmin):
    pass


@admin.register(ResetPasswordCode)
class ResetPasswordCode(ModelAdmin):
    pass
