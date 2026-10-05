from django import forms
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _


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
