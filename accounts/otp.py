import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Sum
from django.utils import timezone
from django.utils.module_loading import import_string

from .models import OTPPurpose, SMSOTPChallenge


SUPPORTED_LANGUAGES = {"en", "ta", "ar"}


class OTPError(Exception):
    pass


class OTPRateLimitError(OTPError):
    pass


class OTPVerificationError(OTPError):
    pass


def normalize_phone_number(value):
    value = (value or "").strip()
    if not value:
        return ""

    value = re.sub(r"[^0-9+]", "", value)
    if value.startswith("00"):
        value = "+" + value[2:]

    default_country_code = str(
        getattr(settings, "SMS_DEFAULT_COUNTRY_CODE", "+94") or ""
    ).strip()
    if value.startswith("0") and default_country_code.startswith("+"):
        value = default_country_code + value[1:]

    return value


def mask_phone_number(value):
    value = normalize_phone_number(value)
    if len(value) <= 4:
        return value
    return f"{'*' * max(0, len(value) - 4)}{value[-4:]}"


def _generate_code():
    length = int(getattr(settings, "OTP_CODE_LENGTH", 6))
    lower = 10 ** (length - 1)
    upper = (10 ** length) - 1
    return str(secrets.randbelow(upper - lower + 1) + lower)


def _language_for_user(user):
    language = (getattr(user, "preferred_language", "en") or "en").split("-")[0]
    return language if language in SUPPORTED_LANGUAGES else "en"


def _otp_message(user, code):
    minutes = max(1, int(getattr(settings, "OTP_EXPIRY_SECONDS", 300)) // 60)
    language = _language_for_user(user)

    if language == "ta":
        return (
            f"Sri Lanka Mosque Platform OTP: {code}. "
            f"இது {minutes} நிமிடங்களுக்கு செல்லுபடியாகும். இந்த குறியீட்டை யாருடனும் பகிர வேண்டாம்."
        )
    if language == "ar":
        return (
            f"رمز التحقق لمنصة مساجد سريلانكا: {code}. "
            f"صالح لمدة {minutes} دقائق. لا تشارك هذا الرمز مع أي شخص."
        )
    return (
        f"Sri Lanka Mosque Platform OTP: {code}. "
        f"Valid for {minutes} minutes. Do not share this code with anyone."
    )


def _backend_path():
    return getattr(
        settings,
        "OTP_SMS_BACKEND",
        getattr(
            settings,
            "NOTIFICATION_SMS_BACKEND",
            getattr(
                settings,
                "SUPPORT_SMS_BACKEND",
                "support_requests.sms_backends.ConsoleSMSBackend",
            ),
        ),
    )


def _send_code(challenge, code):
    backend_path = _backend_path()
    try:
        backend_class = import_string(backend_path)
        backend = backend_class()
        result = backend.send_message(
            challenge.phone_number,
            _otp_message(challenge.user, code),
        )
        challenge.provider = getattr(backend, "provider_name", backend_path)
        challenge.last_delivery_error = ""
        challenge.save(update_fields=["provider", "last_delivery_error"])
        return True, str(result or "")
    except Exception as exc:
        challenge.provider = backend_path
        challenge.last_delivery_error = str(exc)
        challenge.save(update_fields=["provider", "last_delivery_error"])
        return False, str(exc)


def _hourly_send_count(phone_number):
    since = timezone.now() - timedelta(hours=1)
    result = SMSOTPChallenge.objects.filter(
        phone_number=phone_number,
        last_sent_at__gte=since,
    ).aggregate(total=Sum("send_count"))
    return int(result["total"] or 0)


def start_otp_challenge(*, user, phone_number, purpose, session_key, target_reference=""):
    phone_number = normalize_phone_number(phone_number)
    if not phone_number:
        raise OTPError("A registered mobile number is required for OTP verification.")

    max_sends = int(getattr(settings, "OTP_MAX_SENDS_PER_HOUR", 5))
    if _hourly_send_count(phone_number) >= max_sends:
        raise OTPRateLimitError(
            "Too many OTP requests were made for this mobile number. Please try again later."
        )

    now = timezone.now()
    SMSOTPChallenge.objects.filter(
        user=user,
        purpose=purpose,
        target_reference=target_reference or "",
        consumed_at__isnull=True,
    ).update(consumed_at=now)

    code = _generate_code()
    challenge = SMSOTPChallenge.objects.create(
        user=user,
        phone_number=phone_number,
        purpose=purpose,
        target_reference=target_reference or "",
        code_hash=make_password(code),
        session_key=session_key or "",
        expires_at=now
        + timedelta(seconds=int(getattr(settings, "OTP_EXPIRY_SECONDS", 300))),
        send_count=1,
    )
    delivered, details = _send_code(challenge, code)
    return challenge, delivered, details


def resend_otp_challenge(challenge):
    if challenge.consumed_at:
        raise OTPVerificationError("This OTP challenge has already been used.")

    now = timezone.now()
    cooldown = int(getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60))
    if challenge.last_sent_at and (now - challenge.last_sent_at).total_seconds() < cooldown:
        remaining = cooldown - int((now - challenge.last_sent_at).total_seconds())
        raise OTPRateLimitError(
            f"Please wait {max(1, remaining)} seconds before requesting another OTP."
        )

    max_sends = int(getattr(settings, "OTP_MAX_SENDS_PER_HOUR", 5))
    if _hourly_send_count(challenge.phone_number) >= max_sends:
        raise OTPRateLimitError(
            "Too many OTP requests were made for this mobile number. Please try again later."
        )

    code = _generate_code()
    challenge.code_hash = make_password(code)
    challenge.expires_at = now + timedelta(
        seconds=int(getattr(settings, "OTP_EXPIRY_SECONDS", 300))
    )
    challenge.verified_at = None
    challenge.attempt_count = 0
    challenge.send_count += 1
    challenge.last_sent_at = now
    challenge.save(
        update_fields=[
            "code_hash",
            "expires_at",
            "verified_at",
            "attempt_count",
            "send_count",
            "last_sent_at",
        ]
    )
    delivered, details = _send_code(challenge, code)
    return delivered, details


def verify_otp_code(challenge, code):
    if challenge.consumed_at:
        raise OTPVerificationError("This OTP has already been used.")

    now = timezone.now()
    if challenge.expires_at <= now:
        raise OTPVerificationError("This OTP has expired. Please request a new code.")

    max_attempts = int(getattr(settings, "OTP_MAX_ATTEMPTS", 5))
    if challenge.attempt_count >= max_attempts:
        raise OTPVerificationError(
            "Too many incorrect attempts. Please request a new OTP."
        )

    if not check_password((code or "").strip(), challenge.code_hash):
        challenge.attempt_count += 1
        challenge.save(update_fields=["attempt_count"])
        remaining = max(0, max_attempts - challenge.attempt_count)
        raise OTPVerificationError(
            f"Invalid OTP. {remaining} attempt(s) remaining."
        )

    challenge.verified_at = now
    challenge.save(update_fields=["verified_at"])
    return challenge


def consume_otp_challenge(challenge):
    if not challenge.consumed_at:
        challenge.consumed_at = timezone.now()
        challenge.save(update_fields=["consumed_at"])
    return challenge

OTP_SESSION_CHALLENGE_KEY = "sms_otp_challenge_id"


def ensure_request_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def attach_challenge_to_session(request, challenge):
    request.session[OTP_SESSION_CHALLENGE_KEY] = challenge.pk
    request.session.modified = True
    return challenge


def clear_challenge_from_session(request):
    request.session.pop(OTP_SESSION_CHALLENGE_KEY, None)
    request.session.modified = True
