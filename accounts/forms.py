from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import UserRole


User = get_user_model()


class UniversalLoginForm(forms.Form):
    identifier = forms.CharField(
        label=_("Username or email"),
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": _("Username or email"),
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": _("Password"),
                "autocomplete": "current-password",
            }
        ),
    )
    remember_me = forms.BooleanField(
        label=_("Remember me"),
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get("identifier")
        password = cleaned_data.get("password")

        if identifier and password:
            self.user_cache = authenticate(
                self.request,
                username=identifier,
                password=password,
            )
            if self.user_cache is None:
                raise forms.ValidationError(
                    _("Invalid username/email or password."),
                    code="invalid_login",
                )
        return cleaned_data

    def get_user(self):
        return self.user_cache

class MosqueAdminRegistrationForm(UserCreationForm):
    """Public sign-up form for users who want to register a mosque.

    The public form never exposes role selection. Every account created here
    is a normal, active Mosque Admin account. Platform/Super Admin roles can
    only be assigned through controlled administration workflows.
    """

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "preferred_language",
        )
        labels = {
            "username": _("Username"),
            "first_name": _("First name"),
            "last_name": _("Last name"),
            "email": _("Email address"),
            "phone_number": _("Mobile number"),
            "preferred_language": _("Preferred language"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["email"].required = True
        self.fields["phone_number"].required = True
        self.fields["preferred_language"].required = True

        text_placeholders = {
            "username": _("Choose a username"),
            "first_name": _("First name"),
            "last_name": _("Last name"),
            "email": _("Email address"),
            "phone_number": _("Registered mobile number"),
            "password1": _("Create a password"),
            "password2": _("Confirm password"),
        }

        autocomplete = {
            "username": "username",
            "first_name": "given-name",
            "last_name": "family-name",
            "email": "email",
            "phone_number": "tel",
            "password1": "new-password",
            "password2": "new-password",
        }

        for name, field in self.fields.items():
            if name == "preferred_language":
                field.widget.attrs.update({"class": "form-select form-select-lg"})
            else:
                field.widget.attrs.update({"class": "form-control form-control-lg"})

            if name in text_placeholders:
                field.widget.attrs["placeholder"] = text_placeholders[name]
            if name in autocomplete:
                field.widget.attrs["autocomplete"] = autocomplete[name]

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                _("An account with this email address already exists.")
            )
        return email

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get("phone_number") or "").strip()
        if User.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError(
                _("An account with this mobile number already exists.")
            )
        return phone_number

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = UserRole.MOSQUE_ADMIN
        user.is_active = True
        user.is_verified = False

        if commit:
            user.save()

        return user

