from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.models import User, UserRole


MANAGED_ROLES = [
    UserRole.MOSQUE_ADMIN,
    UserRole.MOSQUE_STAFF,
    UserRole.DISTRICT_OFFICER,
    UserRole.SUPPORT_OFFICER,
]


def role_choices_for_actor(actor):
    roles = list(MANAGED_ROLES)
    if actor.is_superuser or actor.role == UserRole.SUPER_ADMIN:
        roles.append(UserRole.PLATFORM_ADMIN)

    labels = dict(UserRole.choices)
    return [(role, labels[role]) for role in roles]


class ControlUserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label=_("Confirm password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "role",
            "preferred_language",
            "is_active",
            "is_verified",
        ]

    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = role_choices_for_actor(actor)

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError(_("The two password fields do not match."))

        if password2:
            password_validation.validate_password(password2, self.instance)

        return password2

    def clean_role(self):
        role = self.cleaned_data["role"]
        allowed = {value for value, _label in role_choices_for_actor(self.actor)}
        if role not in allowed:
            raise ValidationError(_("You cannot assign this role."))
        return role

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ControlUserUpdateForm(forms.ModelForm):
    new_password1 = forms.CharField(
        label=_("New password"),
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_("Leave blank to keep the current password."),
    )
    new_password2 = forms.CharField(
        label=_("Confirm new password"),
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "role",
            "preferred_language",
            "is_active",
            "is_verified",
        ]

    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = role_choices_for_actor(actor)

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

    def clean_role(self):
        role = self.cleaned_data["role"]
        allowed = {value for value, _label in role_choices_for_actor(self.actor)}
        if role not in allowed:
            raise ValidationError(_("You cannot assign this role."))
        return role

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("new_password1")
        password2 = cleaned.get("new_password2")

        if password1 or password2:
            if password1 != password2:
                self.add_error(
                    "new_password2",
                    _("The two password fields do not match."),
                )
            elif password2:
                try:
                    password_validation.validate_password(
                        password2,
                        self.instance,
                    )
                except ValidationError as exc:
                    self.add_error("new_password2", exc)

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("new_password1")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user
