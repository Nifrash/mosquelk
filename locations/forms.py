from django import forms

from accounts.models import User, UserRole
from .models import (
    District,
    DistrictOfficerAssignment,
    DivisionalSecretariat,
    GNDivision,
    Province,
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


class ProvinceForm(BootstrapModelForm):
    class Meta:
        model = Province
        fields = ["code", "name_en", "name_ta", "name_ar", "is_active"]


class DistrictForm(BootstrapModelForm):
    class Meta:
        model = District
        fields = ["province", "code", "name_en", "name_ta", "name_ar", "is_active"]


class DivisionalSecretariatForm(BootstrapModelForm):
    class Meta:
        model = DivisionalSecretariat
        fields = ["district", "code", "name_en", "name_ta", "name_ar", "is_active"]


class GNDivisionForm(BootstrapModelForm):
    class Meta:
        model = GNDivision
        fields = [
            "divisional_secretariat",
            "code",
            "name_en",
            "name_ta",
            "name_ar",
            "is_active",
        ]


class DistrictOfficerAssignmentForm(BootstrapModelForm):
    class Meta:
        model = DistrictOfficerAssignment
        fields = ["user", "district", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_user_id = self.instance.user_id if self.instance and self.instance.pk else None
        queryset = User.objects.filter(role=UserRole.DISTRICT_OFFICER, is_active=True)
        if current_user_id:
            queryset = User.objects.filter(
                id=current_user_id
            ) | queryset
        self.fields["user"].queryset = queryset.distinct().order_by("username")
        self.fields["district"].queryset = District.objects.filter(
            is_active=True
        ).select_related("province").order_by("name_en")
