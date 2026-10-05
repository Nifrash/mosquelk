from django.contrib import admin

from .models import (
    MosqueSupportRequest,
    SupportNotification,
    SupportNotificationDelivery,
    SupportRequestDocument,
    SupportRequestHistory,
)


class SupportRequestDocumentInline(admin.TabularInline):
    model = SupportRequestDocument
    extra = 0
    readonly_fields = ("uploaded_by", "created_at")


class SupportRequestHistoryInline(admin.TabularInline):
    model = SupportRequestHistory
    extra = 0
    readonly_fields = (
        "from_status",
        "to_status",
        "actor",
        "notes",
        "created_at",
    )
    can_delete = False


@admin.register(MosqueSupportRequest)
class MosqueSupportRequestAdmin(admin.ModelAdmin):
    list_display = (
        "request_no",
        "mosque",
        "category",
        "priority",
        "status",
        "assigned_to",
        "created_at",
    )
    list_filter = (
        "status",
        "priority",
        "category",
        "mosque__district",
    )
    search_fields = (
        "request_no",
        "title",
        "mosque__mosque_id",
        "mosque__name_en",
        "contact_person",
        "contact_phone",
    )
    readonly_fields = (
        "request_no",
        "created_by",
        "submitted_at",
        "reviewed_at",
        "completed_at",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "mosque",
        "assigned_to",
        "reviewed_by",
    )
    inlines = [
        SupportRequestDocumentInline,
        SupportRequestHistoryInline,
    ]


@admin.register(SupportRequestDocument)
class SupportRequestDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "support_request", "uploaded_by", "created_at")
    search_fields = ("title", "support_request__request_no")


@admin.register(SupportRequestHistory)
class SupportRequestHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "support_request",
        "from_status",
        "to_status",
        "actor",
        "created_at",
    )
    list_filter = ("from_status", "to_status")
    search_fields = ("support_request__request_no", "notes")
    readonly_fields = (
        "support_request",
        "from_status",
        "to_status",
        "actor",
        "notes",
        "created_at",
    )


@admin.register(SupportNotification)
class SupportNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "notification_type",
        "support_request",
        "is_read",
        "created_at",
    )
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "support_request__request_no",
        "title",
        "message",
    )
    readonly_fields = ("created_at", "read_at")


@admin.register(SupportNotificationDelivery)
class SupportNotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "notification",
        "channel",
        "recipient",
        "status",
        "provider",
        "attempted_at",
    )
    list_filter = ("channel", "status", "attempted_at")
    search_fields = (
        "notification__support_request__request_no",
        "notification__user__username",
        "recipient",
        "details",
    )
    readonly_fields = ("attempted_at",)
