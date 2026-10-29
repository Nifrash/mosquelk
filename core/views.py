import hashlib
import logging
import re
import time

from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.core.cache import cache
from django.core.mail import BadHeaderError, EmailMessage
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from locations.models import District, DivisionalSecretariat
from mosques.models import DocumentType, Mosque, MosqueMembership, MosqueStatus
from support_requests.models import MosqueSupportRequest, SupportRequestStatus

from .forms import ContactForm
from .prayer_times_service import (
    PrayerTimesError,
    get_prayer_times_for_address,
    get_prayer_times_for_city,
    get_prayer_times_for_coordinates,
)


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
        "public_support_requests": (
            MosqueSupportRequest.objects.filter(
                status__in=[
                    SupportRequestStatus.APPROVED,
                    SupportRequestStatus.IN_PROGRESS,
                ],
                mosque__status=MosqueStatus.APPROVED,
            )
            .select_related(
                "mosque",
                "mosque__district",
                "mosque__province",
            )
            .order_by("-reviewed_at", "-updated_at")[:6]
        ),
    }
    return render(request, "core/home.html", context)


def about(request):
    return render(request, "core/about.html")


def services(request):
    return render(request, "core/services.html")


logger = logging.getLogger(__name__)

# Every accepted public Contact form message is sent here.
CONTACT_FORM_RECIPIENT = "info@mosques.lk"

CONTACT_FORM_SALT = "core.contact-form"
CONTACT_FORM_MIN_SECONDS = 2
CONTACT_FORM_MAX_AGE_SECONDS = 60 * 60 * 2

# Browser/session abuse controls. These do not replace CSRF; they add another
# lightweight anti-spam layer without requiring an external CAPTCHA service.
CONTACT_ATTEMPT_WINDOW_SECONDS = 60 * 15
CONTACT_MAX_ATTEMPTS_PER_SESSION = 10
CONTACT_SUCCESS_COOLDOWN_SECONDS = 30
CONTACT_MAX_EMAIL_SUBMISSIONS_PER_HOUR = 5


def _new_contact_form_token():
    return signing.dumps(
        {"created_at": time.time()},
        salt=CONTACT_FORM_SALT,
        compress=True,
    )


def _contact_token_is_valid(token):
    if not token:
        return False

    try:
        payload = signing.loads(
            token,
            salt=CONTACT_FORM_SALT,
            max_age=CONTACT_FORM_MAX_AGE_SECONDS,
        )
        created_at = float(payload.get("created_at", 0))
    except (
        signing.BadSignature,
        signing.SignatureExpired,
        TypeError,
        ValueError,
    ):
        return False

    age = time.time() - created_at

    return (
        CONTACT_FORM_MIN_SECONDS
        <= age
        <= CONTACT_FORM_MAX_AGE_SECONDS
    )


def _contact_session_attempt_allowed(request):
    """
    Limit repeated POST attempts from the same browser session.

    The list is stored in Django's server-side session data and contains only
    timestamps, not contact-form content.
    """
    now = time.time()

    attempts = request.session.get(
        "_contact_form_attempts",
        [],
    )

    attempts = [
        float(timestamp)
        for timestamp in attempts
        if now - float(timestamp)
        < CONTACT_ATTEMPT_WINDOW_SECONDS
    ]

    if len(attempts) >= CONTACT_MAX_ATTEMPTS_PER_SESSION:
        request.session["_contact_form_attempts"] = attempts
        request.session.modified = True
        return False

    attempts.append(now)

    request.session["_contact_form_attempts"] = attempts
    request.session.modified = True

    return True


def _contact_success_cooldown_active(request):
    last_success = request.session.get(
        "_contact_form_last_success"
    )

    if not last_success:
        return False

    try:
        elapsed = time.time() - float(last_success)
    except (TypeError, ValueError):
        return False

    return elapsed < CONTACT_SUCCESS_COOLDOWN_SECONDS


def _contact_email_rate_limited(email):
    """
    Limit successful submissions using the same email address.

    Only a SHA-256 digest of the normalized email address is used in the
    cache key; the raw address is not stored in the key.
    """
    normalized = email.strip().lower()
    digest = hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()

    cache_key = f"contact-form-email:{digest}"

    try:
        count = int(cache.get(cache_key, 0) or 0)
    except (TypeError, ValueError):
        count = 0

    return count >= CONTACT_MAX_EMAIL_SUBMISSIONS_PER_HOUR


def _record_contact_email_submission(email):
    normalized = email.strip().lower()
    digest = hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()

    cache_key = f"contact-form-email:{digest}"

    # `add` is atomic on supported cache backends. If the key already exists,
    # increment it. Failure to increment should never break contact delivery.
    try:
        if not cache.add(
            cache_key,
            1,
            timeout=60 * 60,
        ):
            cache.incr(cache_key)
    except Exception:
        logger.warning(
            "Contact form rate-limit cache could not be updated.",
            exc_info=True,
        )


@sensitive_post_parameters(
    "name",
    "email",
    "subject",
    "message",
)
@csrf_protect
@require_http_methods(["GET", "POST"])
def contact(request):
    if request.method == "GET":
        form = ContactForm(
            initial={
                "form_token": _new_contact_form_token(),
            }
        )

        return render(
            request,
            "core/contact.html",
            {"form": form},
        )

    # Count POST attempts before form validation so repeated invalid requests
    # cannot bypass throttling.
    if not _contact_session_attempt_allowed(request):
        form = ContactForm(request.POST)
        form.add_error(
            None,
            _(
                "Too many contact-form attempts were received. "
                "Please wait a few minutes and try again."
            ),
        )

        return render(
            request,
            "core/contact.html",
            {"form": form},
            status=429,
        )

    form = ContactForm(request.POST)

    if not form.is_valid():
        return render(
            request,
            "core/contact.html",
            {"form": form},
            status=400,
        )

    if not _contact_token_is_valid(
        form.cleaned_data["form_token"]
    ):
        form.add_error(
            None,
            _(
                "This contact form has expired or was submitted too quickly. "
                "Please refresh the page and try again."
            ),
        )

        return render(
            request,
            "core/contact.html",
            {"form": form},
            status=400,
        )

    if _contact_success_cooldown_active(request):
        form.add_error(
            None,
            _(
                "Your previous message was just sent. "
                "Please wait a moment before sending another message."
            ),
        )

        return render(
            request,
            "core/contact.html",
            {"form": form},
            status=429,
        )

    name = form.cleaned_data["name"]
    email = form.cleaned_data["email"]
    subject = form.cleaned_data["subject"]
    message_text = form.cleaned_data["message"]

    if _contact_email_rate_limited(email):
        form.add_error(
            None,
            _(
                "Too many messages have recently been submitted using this "
                "email address. Please try again later."
            ),
        )

        return render(
            request,
            "core/contact.html",
            {"form": form},
            status=429,
        )

    received_at = timezone.localtime().strftime(
        "%Y-%m-%d %H:%M:%S %Z"
    )

    body = (
        "New contact-form message from Mosques Sri Lanka\n"
        "================================================\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Subject: {subject}\n"
        f"Received: {received_at}\n\n"
        "Message\n"
        "-------\n"
        f"{message_text}\n"
    )

    email_message = EmailMessage(
        subject=f"[Mosques Sri Lanka Contact] {subject}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        # Intentionally fixed so all Contact page messages reach this inbox.
        to=[CONTACT_FORM_RECIPIENT],
        # Visitor email is Reply-To, never From. This avoids sender spoofing
        # and improves SPF/DMARC compatibility.
        reply_to=[email],
    )

    try:
        email_message.send(fail_silently=False)
    except BadHeaderError:
        logger.warning(
            "Rejected invalid header data in Contact form."
        )

        form.add_error(
            None,
            _(
                "Your message could not be sent because some information "
                "was invalid. Please check the form and try again."
            ),
        )

        return render(
            request,
            "core/contact.html",
            {"form": form},
            status=400,
        )
    except Exception:
        # Log server/provider details for administrators, but do not expose
        # SMTP/provider error information to the public user.
        logger.exception(
            "Contact form email delivery failed."
        )

        form.add_error(
            None,
            _(
                "We could not send your message at the moment. "
                "Please try again shortly or email info@mosques.lk directly."
            ),
        )

        return render(
            request,
            "core/contact.html",
            {"form": form},
            status=503,
        )

    _record_contact_email_submission(email)

    request.session["_contact_form_last_success"] = (
        time.time()
    )
    request.session.modified = True

    messages.success(
        request,
        _(
            "Your message has been sent successfully to info@mosques.lk. "
            "Our team will respond as soon as possible."
        ),
    )

    return redirect("core:contact")


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
SRI_LANKA_PROVINCE_COORDINATES = {
    "central": (7.382, 80.723),
    "eastern": (7.750, 81.412),
    "north central": (8.281, 80.485),
    "north western": (7.913, 80.107),
    "northern": (9.180, 80.481),
    "sabaragamuwa": (6.813, 80.335),
    "southern": (6.249, 80.461),
    "uva": (6.954, 81.235),
    "western": (6.828, 80.033),
}


def _normalise_province_name(value):
    value = (value or "").strip().lower()

    for suffix in (" province", " පළාත", " மாகாணம்"):
        if value.endswith(suffix):
            value = value[: -len(suffix)].strip()

    return value

# ============================================================
# PUBLIC PRAYER TIMES / ALADHAN API
# ============================================================

@require_http_methods(["GET"])
def prayer_times_home(request):
    """
    Prayer Times Near Me.

    The browser asks the visitor for geolocation permission. Coordinates are
    posted to `prayer_times_current_api`; they are not saved to a model.
    """
    return render(
        request,
        "core/prayer_times/home.html",
    )


@csrf_protect
@require_http_methods(["POST"])
def prayer_times_current_api(request):
    """
    Calculate prayer times from browser-provided coordinates.

    POST is used so precise coordinates do not appear in normal page URLs.
    """
    latitude = request.POST.get("latitude")
    longitude = request.POST.get("longitude")
    selected_date = request.POST.get("date") or None

    try:
        result = get_prayer_times_for_coordinates(
            latitude,
            longitude,
            selected_date,
        )
    except PrayerTimesError as exc:
        return JsonResponse(
            {
                "ok": False,
                "message": str(exc),
            },
            status=502,
        )

    return JsonResponse(
        {
            "ok": True,
            "data": result,
        }
    )


@require_http_methods(["GET"])
def prayer_times_ds_index(request):
    return render(
        request,
        "core/prayer_times/ds_index.html",
    )


@require_http_methods(["GET"])
def prayer_times_ds_suggestions(request):
    """
    Search active Sri Lanka Divisional Secretariats.

    The query is intentionally limited and results only come from the local
    official-location master data already loaded into this project.
    """
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"results": []})

    if len(query) > 100:
        query = query[:100]

    queryset = (
        DivisionalSecretariat.objects.filter(
            is_active=True,
        )
        .select_related(
            "district",
            "district__province",
        )
        .filter(
            Q(name_en__icontains=query)
            | Q(name_ta__icontains=query)
            | Q(name_ar__icontains=query)
            | Q(code__icontains=query)
            | Q(district__name_en__icontains=query)
            | Q(district__name_ta__icontains=query)
            | Q(district__name_ar__icontains=query)
            | Q(district__province__name_en__icontains=query)
        )
        .order_by(
            "name_en",
            "district__name_en",
        )[:12]
    )

    results = []

    for ds in queryset:
        district = ds.district
        province = district.province

        results.append(
            {
                "id": ds.pk,
                "name": ds.localized_name,
                "name_en": ds.name_en,
                "district": district.localized_name,
                "province": province.localized_name,
                "code": ds.code,
                "url": reverse(
                    "core:prayer_times_ds_detail",
                    kwargs={"ds_id": ds.pk},
                ),
            }
        )

    return JsonResponse({"results": results})


def _get_ds_prayer_times(ds, selected_date=None):
    """
    Resolve prayer times for a Sri Lanka Divisional Secretariat.

    Resolution order:
    1. Full DS + District + Province address
    2. DS name as a city in Sri Lanka
    3. District name as a city in Sri Lanka

    The final District fallback is explicitly marked as approximate.
    """
    district = ds.district
    province = district.province

    full_address = (
        f"{ds.name_en}, "
        f"{district.name_en}, "
        f"{province.name_en}, "
        "Sri Lanka"
    )

    errors = []

    try:
        return (
            get_prayer_times_for_address(
                full_address,
                selected_date,
                timezone_name="Asia/Colombo",
                location_label=(
                    f"{ds.localized_name}, "
                    f"{district.localized_name}"
                ),
                precision="divisional_secretariat",
            ),
            False,
        )
    except PrayerTimesError as exc:
        errors.append(str(exc))

    try:
        return (
            get_prayer_times_for_city(
                ds.name_en,
                "Sri Lanka",
                selected_date,
                timezone_name="Asia/Colombo",
                location_label=(
                    f"{ds.localized_name}, "
                    f"{district.localized_name}"
                ),
                precision="divisional_secretariat_city",
            ),
            False,
        )
    except PrayerTimesError as exc:
        errors.append(str(exc))

    try:
        return (
            get_prayer_times_for_city(
                district.name_en,
                "Sri Lanka",
                selected_date,
                timezone_name="Asia/Colombo",
                location_label=(
                    f"{district.localized_name}, "
                    f"{province.localized_name}"
                ),
                precision="district_fallback",
            ),
            True,
        )
    except PrayerTimesError as exc:
        errors.append(str(exc))

    # Final reliability fallback:
    # use a known Sri Lanka province-centre coordinate when AlAdhan cannot
    # resolve the selected administrative name, DS name, or District name.
    province_key = _normalise_province_name(province.name_en)
    province_coordinates = SRI_LANKA_PROVINCE_COORDINATES.get(
        province_key
    )

    if province_coordinates:
        try:
            latitude, longitude = province_coordinates

            result = get_prayer_times_for_coordinates(
                latitude,
                longitude,
                selected_date,
            )

            result["location_label"] = (
                f"{province.localized_name}, Sri Lanka"
            )
            result["precision"] = "province_fallback"

            return result, True
        except PrayerTimesError as exc:
            errors.append(str(exc))

    raise PrayerTimesError(
        errors[-1]
        if errors
        else "Prayer times are temporarily unavailable."
    )


@require_http_methods(["GET"])
def prayer_times_ds_api(request, ds_id):
    """
    JSON prayer times for the selected DS.

    Used by the autocomplete page so the prayer table appears immediately
    without navigating away from the search screen.
    """
    ds = get_object_or_404(
        DivisionalSecretariat.objects.select_related(
            "district",
            "district__province",
        ),
        pk=ds_id,
        is_active=True,
    )

    selected_date = (
        request.GET.get("date", "").strip()
        or timezone.localdate().isoformat()
    )

    try:
        prayer_data, used_fallback = _get_ds_prayer_times(
            ds,
            selected_date,
        )
    except PrayerTimesError as exc:
        return JsonResponse(
            {
                "ok": False,
                "message": str(exc),
            },
            status=502,
        )

    return JsonResponse(
        {
            "ok": True,
            "data": prayer_data,
            "used_fallback": used_fallback,
            "location": {
                "id": ds.pk,
                "name": ds.localized_name,
                "name_en": ds.name_en,
                "district": ds.district.localized_name,
                "province": ds.district.province.localized_name,
                "code": ds.code,
                "detail_url": reverse(
                    "core:prayer_times_ds_detail",
                    kwargs={"ds_id": ds.pk},
                ),
            },
        }
    )


@require_http_methods(["GET"])
def prayer_times_ds_detail(request, ds_id):
    ds = get_object_or_404(
        DivisionalSecretariat.objects.select_related(
            "district",
            "district__province",
        ),
        pk=ds_id,
        is_active=True,
    )

    selected_date = (
        request.GET.get("date", "").strip()
        or timezone.localdate().isoformat()
    )

    prayer_data = None
    provider_error = ""
    used_fallback = False

    try:
        prayer_data, used_fallback = _get_ds_prayer_times(
            ds,
            selected_date,
        )
    except PrayerTimesError as exc:
        provider_error = str(exc)

    return render(
        request,
        "core/prayer_times/ds_detail.html",
        {
            "divisional_secretariat": ds,
            "district": ds.district,
            "province": ds.district.province,
            "prayer_data": prayer_data,
            "provider_error": provider_error,
            "used_fallback": used_fallback,
            "selected_date": selected_date,
        },
    )
