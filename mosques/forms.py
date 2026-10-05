from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.models import User, UserRole
from locations.models import District, DivisionalSecretariat, GNDivision, Province
from .models import (
    Mosque,
    MosqueCommitteeMember,
    MosqueDocument,
    MosqueMembership,
    MosqueMembershipRole,
    MosqueOperationalProfile,
    MosqueStatus,
)


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"


class MosqueRegistrationForm(BootstrapModelForm):
    class Meta:
        model = Mosque
        fields = [
            "name_en",
            "name_ta",
            "name_ar",
            "category",
            "established_year",
            "existing_registration_number",
            "province",
            "district",
            "divisional_secretariat",
            "gn_division",
            "address_line1",
            "address_line2",
            "city_or_town",
            "postal_code",
            "official_phone",
            "alternate_phone",
            "official_email",
            "website",
            "description_en",
            "description_ta",
            "description_ar",
        ]
        widgets = {
            "description_en": forms.Textarea(attrs={"rows": 3}),
            "description_ta": forms.Textarea(attrs={"rows": 3}),
            "description_ar": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["province"].queryset = Province.objects.filter(
            is_active=True
        ).order_by("name_en")
        self.fields["district"].queryset = District.objects.none()
        self.fields["divisional_secretariat"].queryset = DivisionalSecretariat.objects.none()
        self.fields["gn_division"].queryset = GNDivision.objects.none()

        province_id = self.data.get("province") or getattr(self.instance, "province_id", None)
        district_id = self.data.get("district") or getattr(self.instance, "district_id", None)
        ds_id = self.data.get("divisional_secretariat") or getattr(
            self.instance,
            "divisional_secretariat_id",
            None,
        )

        if province_id:
            self.fields["district"].queryset = District.objects.filter(
                province_id=province_id,
                is_active=True,
            ).order_by("name_en")

        if district_id:
            self.fields["divisional_secretariat"].queryset = DivisionalSecretariat.objects.filter(
                district_id=district_id,
                is_active=True,
            ).order_by("name_en")

        if ds_id:
            self.fields["gn_division"].queryset = GNDivision.objects.filter(
                divisional_secretariat_id=ds_id,
                is_active=True,
            ).order_by("name_en")

        self.fields["divisional_secretariat"].required = False
        self.fields["gn_division"].required = False

        self.fields["province"].widget.attrs.update({"data-location-province": "1"})
        self.fields["district"].widget.attrs.update({"data-location-district": "1"})
        self.fields["divisional_secretariat"].widget.attrs.update({"data-location-ds": "1"})
        self.fields["gn_division"].widget.attrs.update({"data-location-gn": "1"})

    def clean(self):
        cleaned = super().clean()
        province = cleaned.get("province")
        district = cleaned.get("district")
        ds = cleaned.get("divisional_secretariat")
        gn = cleaned.get("gn_division")

        if province and district and district.province_id != province.id:
            self.add_error(
                "district",
                _("The selected district does not belong to the selected province."),
            )

        if ds and district and ds.district_id != district.id:
            self.add_error(
                "divisional_secretariat",
                _("The selected Divisional Secretariat does not belong to the selected district."),
            )

        if gn:
            if not ds:
                self.add_error(
                    "gn_division",
                    _("Select the Divisional Secretariat before selecting a GN Division."),
                )
            elif gn.divisional_secretariat_id != ds.id:
                self.add_error(
                    "gn_division",
                    _("The selected GN Division does not belong to the selected Divisional Secretariat."),
                )

        return cleaned


class MosqueDocumentForm(BootstrapModelForm):
    class Meta:
        model = MosqueDocument
        fields = ["document_type", "title", "file", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_file(self):
        uploaded = self.cleaned_data.get("file")
        if not uploaded:
            return uploaded

        allowed = {".pdf", ".jpg", ".jpeg", ".png"}
        extension = Path(uploaded.name).suffix.lower()
        if extension not in allowed:
            raise ValidationError(
                _("Upload a PDF, JPG, JPEG, or PNG file."),
            )

        max_size = 10 * 1024 * 1024
        if uploaded.size > max_size:
            raise ValidationError(_("The document must be 10 MB or smaller."))

        return uploaded


class MosqueCommitteeMemberForm(BootstrapModelForm):
    class Meta:
        model = MosqueCommitteeMember
        fields = [
            "full_name",
            "designation",
            "phone_number",
            "email",
            "is_primary_contact",
        ]


class MosqueMembershipForm(BootstrapModelForm):
    class Meta:
        model = MosqueMembership
        fields = ["user", "membership_role", "is_active"]

    def __init__(self, *args, mosque=None, **kwargs):
        self.mosque = mosque
        super().__init__(*args, **kwargs)

        qs = User.objects.filter(
            is_active=True,
            role__in=[UserRole.MOSQUE_ADMIN, UserRole.MOSQUE_STAFF],
        ).order_by("username")

        if mosque:
            qs = qs.exclude(mosque_memberships__mosque=mosque)

        self.fields["user"].queryset = qs


class MosqueReviewForm(forms.Form):
    ACTION_APPROVE = MosqueStatus.APPROVED
    ACTION_REJECT = MosqueStatus.REJECTED

    action = forms.ChoiceField(
        choices=[
            (ACTION_APPROVE, _("Approve Registration")),
            (ACTION_REJECT, _("Reject Registration")),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Decision"),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        label=_("Review notes"),
    )

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get("action")
        notes = (cleaned.get("notes") or "").strip()

        if action == MosqueStatus.REJECTED and not notes:
            self.add_error(
                "notes",
                _("Review notes are required when rejecting a mosque registration."),
            )

        return cleaned


class MosqueOperationalProfileForm(BootstrapModelForm):
    class Meta:
        model = MosqueOperationalProfile
        fields = [
            "public_phone",
            "whatsapp_number",
            "public_email",
            "imam_name",
            "muezzin_name",
            "jummah_prayer_time",
            "capacity_men",
            "capacity_women",
            "has_womens_prayer_area",
            "has_parking",
            "wheelchair_accessible",
            "has_wudu_facilities",
            "has_madrasa",
            "public_summary_en",
            "public_summary_ta",
            "public_summary_ar",
            "facebook_url",
            "youtube_url",
        ]
        widgets = {
            "jummah_prayer_time": forms.TimeInput(attrs={"type": "time"}),
            "public_summary_en": forms.Textarea(attrs={"rows": 4}),
            "public_summary_ta": forms.Textarea(attrs={"rows": 4}),
            "public_summary_ar": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in [
            "has_womens_prayer_area",
            "has_parking",
            "wheelchair_accessible",
            "has_wudu_facilities",
            "has_madrasa",
        ]:
            self.fields[name].widget.attrs["class"] = "form-check-input"
