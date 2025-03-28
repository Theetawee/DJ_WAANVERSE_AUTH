from django.contrib import admin

from .models import Account


class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email_address",
        "is_active",
        "is_staff",
        "username",
        "last_login",
        "date_joined",
    )

    # Define fields to be searchable
    search_fields = ("email_address", "name", "username")

    # Define fields that should be read-only
    readonly_fields = ("last_login", "date_joined")

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
                    "email_address",
                    "username",
                    "name",
                    "password1",
                    "password2",
                    "date_of_birth",
                    "phone_number",
                )
            },
        ),
    )


admin.site.register(Account, AccountAdmin)
