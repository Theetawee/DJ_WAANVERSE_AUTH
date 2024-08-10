from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from unfold.forms import (AdminPasswordChangeForm, UserChangeForm,
                          UserCreationForm)

from .models import Account

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
                    "phone_number",
                    "profile_image",
                     )
            },
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # Define which fields to include in filter options
    list_filter = ("is_active", "is_staff", "is_superuser", "date_of_birth", )

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
                    "phone_number",
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
                        "phone_number",
                        "profile_image",
                    )
                },
            ),
        )


admin.site.register(Account, AccountAdmin)
