from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import (
    MosqueAdminRegistrationForm,
    SMSOTPVerificationForm,
    UniversalLoginForm,
)
from .models import OTPPurpose, SMSOTPChallenge, UserRole
from .otp import (
    OTPError,
    OTPRateLimitError,
    OTPVerificationError,
    OTP_SESSION_CHALLENGE_KEY,
    attach_challenge_to_session,
    clear_challenge_from_session,
    consume_otp_challenge,
    ensure_request_session_key,
    mask_phone_number,
    resend_otp_challenge,
    start_otp_challenge,
    verify_otp_code,
)


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

        messages.success(
            request,
            _("Welcome back, %(name)s.")
            % {"name": user.get_full_name() or user.username},
        )

        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect("dashboard:home")

    return render(request, "accounts/login.html", {"form": form, "next": next_url})


def mosque_admin_register(request):
    """Create a Mosque Admin account pending SMS OTP verification."""

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

        try:
            challenge, delivered, _details = start_otp_challenge(
                user=user,
                phone_number=user.phone_number,
                purpose=OTPPurpose.ACCOUNT_REGISTRATION,
                session_key=ensure_request_session_key(request),
                target_reference=str(user.pk),
            )
        except OTPError as exc:
            messages.error(
                request,
                _("Account created but OTP verification could not start: %(error)s")
                % {"error": str(exc)},
            )
            return redirect("accounts:login")

        attach_challenge_to_session(request, challenge)

        if delivered:
            messages.info(
                request,
                _("We sent a 6-digit SMS OTP to your registered mobile number."),
            )
        else:
            messages.warning(
                request,
                _("Your account was created, but SMS delivery failed. Use Resend OTP on the verification page."),
            )

        return redirect("accounts:otp_verify")

    return render(
        request,
        "accounts/mosque_admin_register.html",
        {"form": form},
    )


def _get_session_challenge(request):
    challenge_id = request.session.get(OTP_SESSION_CHALLENGE_KEY)
    if not challenge_id:
        return None

    session_key = ensure_request_session_key(request)
    return SMSOTPChallenge.objects.filter(
        pk=challenge_id,
        session_key=session_key,
    ).select_related("user").first()


def _complete_verified_action(request, challenge):
    """Execute the business action only after the SMS OTP has been verified."""

    if not challenge.is_verified or challenge.is_consumed:
        raise PermissionDenied

    if challenge.purpose == OTPPurpose.ACCOUNT_REGISTRATION:
        user = challenge.user
        if not user:
            raise PermissionDenied

        user.is_active = True
        user.is_verified = True
        user.save(update_fields=["is_active", "is_verified", "updated_at"])

        consume_otp_challenge(challenge)
        clear_challenge_from_session(request)

        login(
            request,
            user,
            backend="accounts.backends.UsernameOrEmailBackend",
        )
        messages.success(
            request,
            _("Your mobile number has been verified. You can now register your mosque."),
        )
        return redirect("mosques:create")

    if not request.user.is_authenticated:
        raise PermissionDenied

    if challenge.user_id != request.user.id:
        raise PermissionDenied

    if challenge.purpose == OTPPurpose.MOSQUE_SUBMISSION:
        from mosques.services import submit_mosque_registration

        mosque = submit_mosque_registration(
            mosque_id=challenge.target_reference,
            user=request.user,
        )
        consume_otp_challenge(challenge)
        clear_challenge_from_session(request)
        messages.success(
            request,
            _("OTP verified. Mosque registration submitted successfully for Platform Admin approval."),
        )
        return redirect("mosques:detail", mosque_id=mosque.mosque_id)

    if challenge.purpose == OTPPurpose.SUPPORT_SUBMISSION:
        from support_requests.services import submit_support_request

        support_request, _is_resubmission = submit_support_request(
            request_no=challenge.target_reference,
            user=request.user,
        )
        consume_otp_challenge(challenge)
        clear_challenge_from_session(request)
        messages.success(
            request,
            _("OTP verified. Support request submitted successfully."),
        )
        return redirect(
            "support_requests:detail",
            request_no=support_request.request_no,
        )

    raise PermissionDenied


def otp_verify(request):
    challenge = _get_session_challenge(request)
    if challenge is None:
        messages.error(request, _("No active OTP verification request was found."))
        return redirect("core:home")

    if challenge.is_consumed:
        clear_challenge_from_session(request)
        messages.info(request, _("This OTP request has already been completed."))
        return redirect("dashboard:home")

    form = SMSOTPVerificationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            verify_otp_code(challenge, form.cleaned_data["code"])
            return _complete_verified_action(request, challenge)
        except OTPVerificationError as exc:
            form.add_error("code", str(exc))
        except PermissionDenied:
            consume_otp_challenge(challenge)
            clear_challenge_from_session(request)
            raise

    return render(
        request,
        "accounts/otp_verify.html",
        {
            "form": form,
            "challenge": challenge,
            "masked_phone": mask_phone_number(challenge.phone_number),
        },
    )


@require_POST
def otp_resend(request):
    challenge = _get_session_challenge(request)
    if challenge is None:
        messages.error(request, _("No active OTP verification request was found."))
        return redirect("core:home")

    try:
        delivered, _details = resend_otp_challenge(challenge)
        if delivered:
            messages.success(request, _("A new SMS OTP has been sent."))
        else:
            messages.error(
                request,
                _("The OTP was regenerated, but SMS delivery failed. Please try again or contact support."),
            )
    except (OTPRateLimitError, OTPVerificationError) as exc:
        messages.error(request, str(exc))

    return redirect("accounts:otp_verify")


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, _("You have been signed out successfully."))
    return redirect("core:home")


@login_required
def profile_view(request):
    return render(request, "accounts/profile.html")
