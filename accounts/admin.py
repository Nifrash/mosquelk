from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "is_verified",
        "is_staff",
        "is_active",
    )
    list_filter = ("role", "is_verified", "is_staff", "is_active", "preferred_language")
    search_fields = ("username", "first_name", "last_name", "email", "phone_number")
    ordering = ("username",)

    fieldsets = UserAdmin.fieldsets + (
        (
            _("Mosque Platform Access"),
            {
                "fields": (
                    "role",
                    "phone_number",
                    "preferred_language",
                    "is_verified",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            _("Mosque Platform Access"),
            {
                "fields": (
                    "email",
                    "role",
                    "phone_number",
                    "preferred_language",
                    "is_verified",
                )
            },
        ),
    )
