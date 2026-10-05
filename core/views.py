import re

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _
from django.utils.http import url_has_allowed_host_and_scheme

from locations.models import District
from mosques.models import DocumentType, Mosque, MosqueMembership, MosqueStatus
from support_requests.models import MosqueSupportRequest, SupportRequestStatus

from .forms import ContactForm


def home(request):
    approved_mosques_qs = (
        Mosque.objects.filter(status=MosqueStatus.APPROVED)
        .select_related("district", "province")
        .prefetch_related("documents")[:4]
    )

    featured_mosques = []
    for mosque in approved_mosques_qs:
        photo = next(
            (
                document
                for document in mosque.documents.all()
                if document.document_type == DocumentType.PHOTO
                and document.file
            ),
            None,
        )
        mosque.home_photo_url = photo.file.url if photo else ""
        featured_mosques.append(mosque)

    context = {
        "approved_mosque_count": Mosque.objects.filter(
            status=MosqueStatus.APPROVED
        ).count(),
        "mosque_member_count": MosqueMembership.objects.filter(
            is_active=True
        ).count(),
        "completed_support_count": MosqueSupportRequest.objects.filter(
            status=SupportRequestStatus.COMPLETED
        ).count(),
        "district_count": District.objects.filter(is_active=True).count(),
        "featured_mosques": featured_mosques,
    }
    return render(request, "core/home.html", context)


def about(request):
    context = {
        "approved_mosque_count": Mosque.objects.filter(
            status=MosqueStatus.APPROVED
        ).count(),
        "completed_support_count": MosqueSupportRequest.objects.filter(
            status=SupportRequestStatus.COMPLETED
        ).count(),
        "district_count": District.objects.filter(is_active=True).count(),
    }
    return render(request, "core/about.html", context)


def services(request):
    return render(request, "core/services.html")


def contact(request):
    form = ContactForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        name = form.cleaned_data["name"]
        email = form.cleaned_data["email"]
        subject = form.cleaned_data["subject"]
        message = form.cleaned_data["message"]

        body = (
            f"Name: {name}\n"
            f"Email: {email}\n\n"
            f"Message:\n{message}"
        )

        email_message = EmailMessage(
            subject=f"[Mosques Sri Lanka] {subject}",
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.CONTACT_EMAIL],
            reply_to=[email],
        )
        email_message.send(fail_silently=False)

        messages.success(
            request,
            _("Your message has been sent successfully. Our team will contact you soon."),
        )
        return redirect("core:contact")

    return render(request, "core/contact.html", {"form": form})


def root_home_redirect(request):
    """
    Bare-domain entry point.

    A new visitor who opens "/" is sent to the default English home page.
    Language switching from there is handled by switch_language().
    """
    default_language = settings.LANGUAGE_CODE

    with translation.override(default_language):
        home_url = reverse("core:home")

    return redirect(home_url)


def _same_page_in_language(url, language_code):
    """
    Replace only the language prefix while preserving the current path
    and query string.

    Examples:
        /en/about/                     -> /ta/about/
        /en/support/?status=SUBMITTED  -> /ar/support/?status=SUBMITTED
    """
    supported_codes = [code for code, _name in settings.LANGUAGES]

    if language_code not in supported_codes:
        raise Http404("Unsupported language.")

    # Only local URLs are accepted by the switcher.
    if not url.startswith("/"):
        url = "/"

    language_pattern = "|".join(
        re.escape(code) for code in supported_codes
    )

    prefix_pattern = rf"^/({language_pattern})(?=/|$)"

    if re.search(prefix_pattern, url):
        return re.sub(
            prefix_pattern,
            f"/{language_code}",
            url,
            count=1,
        )

    # Unprefixed local path: add the language prefix.
    if url == "/":
        return f"/{language_code}/"

    return f"/{language_code}{url}"


def switch_language(request, language_code):
    """
    Reliable same-page language switch for the project's prefixed URLs.

    The navbar sends the current full path in ?next=.
    We change only /en/, /ta/ or /ar/, preserve the rest of the URL,
    activate the language and store it in Django's language cookie.
    """
    supported_codes = {code for code, _name in settings.LANGUAGES}

    if language_code not in supported_codes:
        raise Http404("Unsupported language.")

    next_url = request.GET.get("next", "/")

    # Prevent external/open redirects.
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = "/"

    target_url = _same_page_in_language(
        next_url,
        language_code,
    )

    translation.activate(language_code)

    response = redirect(target_url)

    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        language_code,
        max_age=getattr(
            settings,
            "LANGUAGE_COOKIE_AGE",
            60 * 60 * 24 * 365,
        ),
        path=getattr(
            settings,
            "LANGUAGE_COOKIE_PATH",
            "/",
        ),
        domain=getattr(
            settings,
            "LANGUAGE_COOKIE_DOMAIN",
            None,
        ),
        secure=getattr(
            settings,
            "LANGUAGE_COOKIE_SECURE",
            False,
        ),
        httponly=getattr(
            settings,
            "LANGUAGE_COOKIE_HTTPONLY",
            False,
        ),
        samesite=getattr(
            settings,
            "LANGUAGE_COOKIE_SAMESITE",
            "Lax",
        ),
    )

    return response
