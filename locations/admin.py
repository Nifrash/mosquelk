from django.contrib import admin

from .models import (
    District,
    DistrictOfficerAssignment,
    DivisionalSecretariat,
    GNDivision,
    Province,
)


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("code", "name_en", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name_en", "name_ta", "name_ar")


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("code", "name_en", "province", "is_active")
    list_filter = ("province", "is_active")
    search_fields = ("code", "name_en", "name_ta", "name_ar", "province__name_en")
    autocomplete_fields = ("province",)


@admin.register(DivisionalSecretariat)
class DivisionalSecretariatAdmin(admin.ModelAdmin):
    list_display = ("code", "name_en", "district", "is_active")
    list_filter = ("district__province", "district", "is_active")
    search_fields = ("code", "name_en", "name_ta", "name_ar", "district__name_en")
    autocomplete_fields = ("district",)


@admin.register(GNDivision)
class GNDivisionAdmin(admin.ModelAdmin):
    list_display = ("code", "name_en", "divisional_secretariat", "is_active")
    list_filter = ("divisional_secretariat__district", "is_active")
    search_fields = (
        "code",
        "name_en",
        "name_ta",
        "name_ar",
        "divisional_secretariat__name_en",
        "divisional_secretariat__district__name_en",
    )
    autocomplete_fields = ("divisional_secretariat",)


@admin.register(DistrictOfficerAssignment)
class DistrictOfficerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "district", "is_active", "updated_at")
    list_filter = ("district__province", "district", "is_active")
    search_fields = ("user__username", "user__email", "district__name_en")
    autocomplete_fields = ("user", "district")
