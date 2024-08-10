from django.contrib import admin
from .models import Account


class AccountAdmin(admin.ModelAdmin):
    # Define the fields to be displayed in the list view
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
    list_filter = ("is_active", "is_staff", "is_superuser", "date_of_birth")

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


admin.site.register(Account, AccountAdmin)
