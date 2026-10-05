from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from mosques.models import Mosque, MosqueMembership, MosqueMembershipRole, MosqueStatus

from .models import (
    MosqueSupportRequest,
    SupportRequestDocument,
    SupportRequestStatus,
)


ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class SupportRequestForm(BootstrapModelForm):
    class Meta:
        model = MosqueSupportRequest
        fields = [
            "mosque",
            "category",
            "priority",
            "title",
            "issue_description",
            "requested_support",
            "requested_amount",
            "contact_person",
            "contact_phone",
        ]
        widgets = {
            "issue_description": forms.Textarea(attrs={"rows": 5}),
            "requested_support": forms.Textarea(attrs={"rows": 4}),
            "requested_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, user=None, mosque=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user is None:
            self.fields["mosque"].queryset = Mosque.objects.none()
            return

        mosque_ids = MosqueMembership.objects.filter(
            user=user,
            membership_role=MosqueMembershipRole.ADMIN,
            is_active=True,
            mosque__status=MosqueStatus.APPROVED,
        ).values_list("mosque_id", flat=True)

        queryset = Mosque.objects.filter(
            pk__in=mosque_ids,
            status=MosqueStatus.APPROVED,
        ).order_by("name_en")

        self.fields["mosque"].queryset = queryset

        if mosque is not None and queryset.filter(pk=mosque.pk).exists():
            self.fields["mosque"].initial = mosque

    def clean_mosque(self):
        mosque = self.cleaned_data["mosque"]
        if mosque.status != MosqueStatus.APPROVED:
            raise ValidationError(
                _("Support requests can only be created for approved mosques.")
            )
        return mosque


class SupportRequestDocumentForm(BootstrapModelForm):
    class Meta:
        model = SupportRequestDocument
        fields = ["title", "file", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_file(self):
        file_obj = self.cleaned_data.get("file")
        if not file_obj:
            return file_obj

        extension = Path(file_obj.name).suffix.lower()
        if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
            raise ValidationError(
                _("Only PDF, JPG, JPEG and PNG files are allowed.")
            )

        if file_obj.size > MAX_DOCUMENT_SIZE:
            raise ValidationError(
                _("The maximum file size is 10 MB.")
            )

        return file_obj


class SupportRequestReviewForm(forms.Form):
    action = forms.ChoiceField(choices=[])
    approved_amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
        min_value=0,
        label=_("Approved amount (LKR)"),
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
    )
    notes = forms.CharField(
        required=False,
        label=_("Officer note / requested information"),
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    ACTIONS_BY_STATUS = {
        SupportRequestStatus.SUBMITTED: [
            (SupportRequestStatus.UNDER_REVIEW, _("Mark Under Review")),
            (SupportRequestStatus.DOCUMENTS_REQUIRED, _("Request Additional Information / Documents")),
            (SupportRequestStatus.APPROVED, _("Approve Request")),
            (SupportRequestStatus.REJECTED, _("Reject Request")),
        ],
        SupportRequestStatus.UNDER_REVIEW: [
            (SupportRequestStatus.DOCUMENTS_REQUIRED, _("Request Additional Information / Documents")),
            (SupportRequestStatus.APPROVED, _("Approve Request")),
            (SupportRequestStatus.REJECTED, _("Reject Request")),
        ],
        SupportRequestStatus.APPROVED: [
            (SupportRequestStatus.IN_PROGRESS, _("Mark In Progress")),
            (SupportRequestStatus.COMPLETED, _("Mark Completed")),
        ],
        SupportRequestStatus.IN_PROGRESS: [
            (SupportRequestStatus.COMPLETED, _("Mark Completed")),
        ],
    }

    def __init__(self, *args, support_request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.support_request = support_request
        current_status = support_request.status if support_request else None
        self.fields["action"].choices = self.ACTIONS_BY_STATUS.get(
            current_status,
            [],
        )

        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

        if current_status not in {
            SupportRequestStatus.SUBMITTED,
            SupportRequestStatus.UNDER_REVIEW,
        }:
            self.fields["approved_amount"].widget.attrs["disabled"] = True

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        notes = (cleaned_data.get("notes") or "").strip()

        valid_actions = {
            value for value, _label in self.fields["action"].choices
        }
        if action and action not in valid_actions:
            raise ValidationError(_("This status change is not allowed."))

        if action in {
            SupportRequestStatus.DOCUMENTS_REQUIRED,
            SupportRequestStatus.REJECTED,
        } and not notes:
            self.add_error(
                "notes",
                _("Please specify the additional information/documents required, or provide the rejection reason."),
            )

        return cleaned_data
