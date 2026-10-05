from django import forms
from django.utils.translation import gettext_lazy as _


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=160,
        label=_("Name"),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Your name"),
                "autocomplete": "name",
            }
        ),
    )
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Email address"),
                "autocomplete": "email",
            }
        ),
    )
    subject = forms.CharField(
        max_length=200,
        label=_("Subject"),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("How can we help?"),
            }
        ),
    )
    message = forms.CharField(
        label=_("Message"),
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 6,
                "placeholder": _("Write your message here"),
            }
        ),
    )
