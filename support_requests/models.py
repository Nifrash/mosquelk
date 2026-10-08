from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from mosques.models import Mosque, MosqueStatus


class SupportCategory(models.TextChoices):
    MOSQUE_ISSUE = "MOSQUE_ISSUE", _("General Mosque Issue")
    CONSTRUCTION = "CONSTRUCTION", _("Construction")
    RENOVATION = "RENOVATION", _("Renovation / Repair")
    SALARY = "SALARY", _("Imam / Muezzin / Staff Salary")
    UTILITIES = "UTILITIES", _("Water / Electricity / Utilities")
    MAINTENANCE = "MAINTENANCE", _("Maintenance")
    EQUIPMENT = "EQUIPMENT", _("Furniture / Equipment")
    FINANCIAL = "FINANCIAL", _("Financial Assistance")
    EDUCATION = "EDUCATION", _("Religious / Educational Program")
    EMERGENCY = "EMERGENCY", _("Emergency Assistance")
    OTHER = "OTHER", _("Other")


class SupportPriority(models.TextChoices):
    NORMAL = "NORMAL", _("Normal")
    HIGH = "HIGH", _("High")
    URGENT = "URGENT", _("Urgent")


class SupportRequestStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    SUBMITTED = "SUBMITTED", _("Submitted")
    UNDER_REVIEW = "UNDER_REVIEW", _("Under Review")
    DOCUMENTS_REQUIRED = "DOCUMENTS_REQUIRED", _("Additional Information / Documents Required")
    APPROVED = "APPROVED", _("Approved")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    COMPLETED = "COMPLETED", _("Completed")
    REJECTED = "REJECTED", _("Rejected")
    CANCELLED = "CANCELLED", _("Cancelled")


TERMINAL_SUPPORT_STATUSES = {
    SupportRequestStatus.COMPLETED,
    SupportRequestStatus.REJECTED,
    SupportRequestStatus.CANCELLED,
}


class MosqueSupportRequest(models.Model):
    request_no = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        db_index=True,
    )
    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.PROTECT,
        related_name="support_requests",
    )
    category = models.CharField(
        max_length=30,
        choices=SupportCategory.choices,
        db_index=True,
    )
    priority = models.CharField(
        max_length=15,
        choices=SupportPriority.choices,
        default=SupportPriority.NORMAL,
        db_index=True,
    )
    title = models.CharField(max_length=220)
    issue_description = models.TextField(
        verbose_name=_("Describe the issue / current situation"),
    )
    requested_support = models.TextField(
        verbose_name=_("Support requested"),
    )
    requested_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Requested amount (LKR)"),
    )

    contact_person = models.CharField(max_length=180)
    contact_phone = models.CharField(max_length=30)

    status = models.CharField(
        max_length=25,
        choices=SupportRequestStatus.choices,
        default=SupportRequestStatus.DRAFT,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_support_requests",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_support_requests",
        null=True,
        blank=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_support_requests",
        null=True,
        blank=True,
    )

    approved_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Approved amount (LKR)"),
    )
    latest_admin_note = models.TextField(blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"], name="support_status_priority_idx"),
            models.Index(fields=["mosque", "status"], name="support_mosque_status_idx"),
            models.Index(fields=["category"], name="support_category_idx"),
        ]
        verbose_name = _("mosque support request")
        verbose_name_plural = _("mosque support requests")

    def __str__(self):
        return f"{self.request_no or 'New'} - {self.title}"

    @property
    def is_editable_by_mosque(self):
        return self.status in {
            SupportRequestStatus.DRAFT,
            SupportRequestStatus.DOCUMENTS_REQUIRED,
        }

    @property
    def is_terminal(self):
        return self.status in TERMINAL_SUPPORT_STATUSES

    def clean(self):
        super().clean()

        if self.mosque_id and self.mosque.status != MosqueStatus.APPROVED:
            raise ValidationError(
                {"mosque": _("Support requests can only be created for approved mosques.")}
            )

        if self.requested_amount is not None and self.requested_amount < 0:
            raise ValidationError(
                {"requested_amount": _("Requested amount cannot be negative.")}
            )

        if self.approved_amount is not None and self.approved_amount < 0:
            raise ValidationError(
                {"approved_amount": _("Approved amount cannot be negative.")}
            )

    def save(self, *args, **kwargs):
        is_new_without_number = self.pk is None and not self.request_no
        super().save(*args, **kwargs)

        if is_new_without_number:
            year = self.created_at.year if self.created_at else timezone.localdate().year
            self.request_no = f"SUP-{year}-{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(request_no=self.request_no)


def support_document_upload_to(instance, filename):
    safe_name = Path(filename).name
    request_ref = instance.support_request.request_no or f"request-{instance.support_request_id}"
    return f"support_requests/{request_ref}/documents/{safe_name}"


class SupportRequestDocument(models.Model):
    support_request = models.ForeignKey(
        MosqueSupportRequest,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    title = models.CharField(max_length=180)
    file = models.FileField(upload_to=support_document_upload_to)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="uploaded_support_request_documents",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class SupportRequestHistory(models.Model):
    support_request = models.ForeignKey(
        MosqueSupportRequest,
        on_delete=models.CASCADE,
        related_name="history",
    )
    from_status = models.CharField(
        max_length=25,
        choices=SupportRequestStatus.choices,
    )
    to_status = models.CharField(
        max_length=25,
        choices=SupportRequestStatus.choices,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="support_request_actions",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("support request history")
        verbose_name_plural = _("support request history")

    def __str__(self):
        return f"{self.support_request.request_no}: {self.from_status} → {self.to_status}"


class NotificationCategory(models.TextChoices):
    MOSQUE = "MOSQUE", _("Mosque Registration")
    SUPPORT = "SUPPORT", _("Support Requests")
    ACCESS = "ACCESS", _("Mosque Access")
    ACCOUNT = "ACCOUNT", _("Account")
    ASSIGNMENT = "ASSIGNMENT", _("Officer Assignment")
    SYSTEM = "SYSTEM", _("System")


class NotificationPriority(models.TextChoices):
    NORMAL = "NORMAL", _("Normal")
    HIGH = "HIGH", _("High")


class SupportNotificationType(models.TextChoices):
    # Support request events (existing + Phase 9 extensions)
    REQUEST_SUBMITTED = "REQUEST_SUBMITTED", _("Support Request Submitted")
    REQUEST_RESUBMITTED = "REQUEST_RESUBMITTED", _("Support Request Resubmitted")
    REQUEST_UNDER_REVIEW = "REQUEST_UNDER_REVIEW", _("Support Request Under Review")
    DOCUMENTS_REQUIRED = "DOCUMENTS_REQUIRED", _("Additional Information / Documents Required")
    REQUEST_APPROVED = "REQUEST_APPROVED", _("Support Request Approved")
    REQUEST_REJECTED = "REQUEST_REJECTED", _("Support Request Rejected")
    REQUEST_IN_PROGRESS = "REQUEST_IN_PROGRESS", _("Support Request In Progress")
    REQUEST_COMPLETED = "REQUEST_COMPLETED", _("Support Request Completed")

    # Mosque registration events
    MOSQUE_SUBMITTED = "MOSQUE_SUBMITTED", _("Mosque Registration Submitted")
    MOSQUE_APPROVED = "MOSQUE_APPROVED", _("Mosque Registration Approved")
    MOSQUE_REJECTED = "MOSQUE_REJECTED", _("Mosque Registration Rejected")

    # Mosque membership/access events
    MOSQUE_ACCESS_ADDED = "MOSQUE_ACCESS_ADDED", _("Mosque Access Added")
    MOSQUE_ACCESS_REMOVED = "MOSQUE_ACCESS_REMOVED", _("Mosque Access Removed")

    # Account management events
    ACCOUNT_CREATED = "ACCOUNT_CREATED", _("Account Created")
    ACCOUNT_ACTIVATED = "ACCOUNT_ACTIVATED", _("Account Activated")
    ACCOUNT_DEACTIVATED = "ACCOUNT_DEACTIVATED", _("Account Deactivated")
    ACCOUNT_ROLE_CHANGED = "ACCOUNT_ROLE_CHANGED", _("Account Role Changed")

    # Officer assignment events
    DISTRICT_ASSIGNED = "DISTRICT_ASSIGNED", _("District Assigned")
    DISTRICT_ASSIGNMENT_REMOVED = "DISTRICT_ASSIGNMENT_REMOVED", _("District Assignment Removed")


class SupportNotification(models.Model):
    """
    Phase 9 platform-wide notification record.

    The model name/table are intentionally retained from Phase 6 so existing
    support-notification history is preserved. It now supports platform events
    that are not tied to a support request.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_notifications",
    )
    support_request = models.ForeignKey(
        MosqueSupportRequest,
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )
    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.SET_NULL,
        related_name="platform_notifications",
        null=True,
        blank=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="generated_platform_notifications",
        null=True,
        blank=True,
    )
    notification_type = models.CharField(
        max_length=50,
        choices=SupportNotificationType.choices,
        db_index=True,
    )
    category = models.CharField(
        max_length=20,
        choices=NotificationCategory.choices,
        default=NotificationCategory.SUPPORT,
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL,
        db_index=True,
    )
    title = models.CharField(max_length=220)
    message = models.TextField()
    action_url = models.CharField(max_length=500, blank=True)
    source_label = models.CharField(max_length=160, blank=True)
    language_code = models.CharField(max_length=10, default="en")
    dashboard_visible = models.BooleanField(default=True, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "is_read", "created_at"],
                name="support_notif_user_read_idx",
            ),
            models.Index(
                fields=["user", "category", "created_at"],
                name="platform_notif_category_idx",
            ),
        ]
        verbose_name = _("platform notification")
        verbose_name_plural = _("platform notifications")

    def __str__(self):
        return f"{self.user}: {self.title}"

    @property
    def reference_label(self):
        if self.source_label:
            return self.source_label
        if self.support_request_id:
            return self.support_request.request_no
        if self.mosque_id:
            return self.mosque.mosque_id
        return ""

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    dashboard_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=True)

    notify_mosque_registration = models.BooleanField(default=True)
    notify_support_requests = models.BooleanField(default=True)
    notify_mosque_access = models.BooleanField(default=True)
    notify_account_changes = models.BooleanField(default=True)
    notify_officer_assignments = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("notification preference")
        verbose_name_plural = _("notification preferences")

    def __str__(self):
        return f"Notification preferences - {self.user}"

    def category_enabled(self, category):
        mapping = {
            NotificationCategory.MOSQUE: self.notify_mosque_registration,
            NotificationCategory.SUPPORT: self.notify_support_requests,
            NotificationCategory.ACCESS: self.notify_mosque_access,
            NotificationCategory.ACCOUNT: self.notify_account_changes,
            NotificationCategory.ASSIGNMENT: self.notify_officer_assignments,
            NotificationCategory.SYSTEM: True,
        }
        return mapping.get(category, True)


class NotificationChannel(models.TextChoices):
    EMAIL = "EMAIL", _("Email")
    SMS = "SMS", _("SMS / Mobile")


class NotificationDeliveryStatus(models.TextChoices):
    SENT = "SENT", _("Sent")
    FAILED = "FAILED", _("Failed")
    SKIPPED = "SKIPPED", _("Skipped")


class SupportNotificationDelivery(models.Model):
    notification = models.ForeignKey(
        SupportNotification,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    channel = models.CharField(
        max_length=10,
        choices=NotificationChannel.choices,
    )
    recipient = models.CharField(max_length=254, blank=True)
    status = models.CharField(
        max_length=12,
        choices=NotificationDeliveryStatus.choices,
    )
    provider = models.CharField(max_length=160, blank=True)
    details = models.TextField(blank=True)
    retry_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="retry_attempts",
        null=True,
        blank=True,
    )
    retried_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="retried_notification_deliveries",
        null=True,
        blank=True,
    )
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-attempted_at"]
        verbose_name = _("notification delivery")
        verbose_name_plural = _("notification deliveries")

    def __str__(self):
        return f"{self.notification_id} - {self.channel} - {self.status}"
