from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import MosqueAdminRegistrationForm, UniversalLoginForm
from .models import UserRole


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    next_url = request.POST.get("next") or request.GET.get("next") or ""
    form = UniversalLoginForm(request=request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)

        if not form.cleaned_data.get("remember_me"):
            request.session.set_expiry(0)

        messages.success(request, _("Welcome back, %(name)s.") % {"name": user.get_full_name() or user.username})

        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect("dashboard:home")

    return render(request, "accounts/login.html", {"form": form, "next": next_url})


def mosque_admin_register(request):
    """Create a public Mosque Admin account and continue to registration."""

    if request.user.is_authenticated:
        if request.user.role == UserRole.MOSQUE_ADMIN:
            return redirect("mosques:create")

        messages.info(
            request,
            _("Mosque registration is available only to Mosque Admin accounts."),
        )
        return redirect("dashboard:home")

    form = MosqueAdminRegistrationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()

        # The project uses this backend for username/email authentication.
        login(
            request,
            user,
            backend="accounts.backends.UsernameOrEmailBackend",
        )

        messages.success(
            request,
            _("Account created successfully. You can now register your mosque."),
        )
        return redirect("mosques:create")

    return render(
        request,
        "accounts/mosque_admin_register.html",
        {"form": form},
    )


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, _("You have been signed out successfully."))
    return redirect("core:home")


@login_required
def profile_view(request):
    return render(request, "accounts/profile.html")
