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


class SupportNotificationType(models.TextChoices):
    REQUEST_SUBMITTED = "REQUEST_SUBMITTED", _("Support Request Submitted")
    REQUEST_RESUBMITTED = "REQUEST_RESUBMITTED", _("Support Request Resubmitted")
    DOCUMENTS_REQUIRED = "DOCUMENTS_REQUIRED", _("Additional Information / Documents Required")
    REQUEST_APPROVED = "REQUEST_APPROVED", _("Support Request Approved")


class SupportNotification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_notifications",
    )
    support_request = models.ForeignKey(
        MosqueSupportRequest,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=40,
        choices=SupportNotificationType.choices,
        db_index=True,
    )
    title = models.CharField(max_length=220)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "is_read", "created_at"],
                name="support_notif_user_read_idx",
            )
        ]
        verbose_name = _("support notification")
        verbose_name_plural = _("support notifications")

    def __str__(self):
        return f"{self.user}: {self.title}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


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
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-attempted_at"]
        verbose_name = _("support notification delivery")
        verbose_name_plural = _("support notification deliveries")

    def __str__(self):
        return f"{self.notification_id} - {self.channel} - {self.status}"
