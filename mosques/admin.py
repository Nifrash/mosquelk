from django.contrib import admin

from .models import (
    Mosque,
    MosqueCommitteeMember,
    MosqueDocument,
    MosqueMembership,
    MosqueOperationalProfile,
    MosqueReviewHistory,
)


class MosqueMembershipInline(admin.TabularInline):
    model = MosqueMembership
    extra = 0


class MosqueCommitteeInline(admin.TabularInline):
    model = MosqueCommitteeMember
    extra = 0


class MosqueDocumentInline(admin.TabularInline):
    model = MosqueDocument
    extra = 0


class MosqueOperationalProfileInline(admin.StackedInline):
    model = MosqueOperationalProfile
    extra = 0
    max_num = 1


@admin.register(Mosque)
class MosqueAdmin(admin.ModelAdmin):
    list_display = (
        "mosque_id",
        "name_en",
        "district",
        "status",
        "created_by",
        "submitted_at",
    )
    list_filter = ("status", "category", "province", "district")
    search_fields = (
        "mosque_id",
        "name_en",
        "name_ta",
        "name_ar",
        "official_email",
        "official_phone",
    )
    autocomplete_fields = (
        "province",
        "district",
        "divisional_secretariat",
        "gn_division",
        "created_by",
        "reviewed_by",
    )
    readonly_fields = (
        "mosque_id",
        "created_at",
        "updated_at",
        "submitted_at",
        "reviewed_at",
    )
    inlines = [MosqueOperationalProfileInline, MosqueMembershipInline, MosqueCommitteeInline, MosqueDocumentInline]


@admin.register(MosqueMembership)
class MosqueMembershipAdmin(admin.ModelAdmin):
    list_display = ("mosque", "user", "membership_role", "is_active")
    list_filter = ("membership_role", "is_active")
    search_fields = ("mosque__mosque_id", "mosque__name_en", "user__username", "user__email")
    autocomplete_fields = ("mosque", "user", "added_by")


@admin.register(MosqueCommitteeMember)
class MosqueCommitteeMemberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "mosque", "designation", "phone_number", "is_primary_contact")
    list_filter = ("designation", "is_primary_contact")
    search_fields = ("full_name", "mosque__name_en", "phone_number", "email")
    autocomplete_fields = ("mosque",)


@admin.register(MosqueDocument)
class MosqueDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "mosque", "document_type", "uploaded_by", "created_at")
    list_filter = ("document_type",)
    search_fields = ("title", "mosque__mosque_id", "mosque__name_en")
    autocomplete_fields = ("mosque", "uploaded_by")


@admin.register(MosqueReviewHistory)
class MosqueReviewHistoryAdmin(admin.ModelAdmin):
    list_display = ("mosque", "from_status", "to_status", "reviewer", "created_at")
    list_filter = ("from_status", "to_status")
    search_fields = ("mosque__mosque_id", "mosque__name_en", "notes")
    autocomplete_fields = ("mosque", "reviewer")
    readonly_fields = ("mosque", "from_status", "to_status", "reviewer", "notes", "created_at")


@admin.register(MosqueOperationalProfile)
class MosqueOperationalProfileAdmin(admin.ModelAdmin):
    list_display = ("mosque", "public_phone", "imam_name", "jummah_prayer_time", "updated_at")
    search_fields = ("mosque__mosque_id", "mosque__name_en", "imam_name", "public_phone", "public_email")
    autocomplete_fields = ("mosque", "updated_by")
    readonly_fields = ("created_at", "updated_at")
