from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils.module_loading import import_string

from accounts.models import UserRole
from mosques.models import MosqueMembership, MosqueMembershipRole

from .models import (
    NotificationChannel,
    NotificationDeliveryStatus,
    SupportNotification,
    SupportNotificationDelivery,
    SupportNotificationType,
)


def _mosque_admin_users(support_request):
    return get_user_model().objects.filter(
        mosque_memberships__mosque=support_request.mosque,
        mosque_memberships__membership_role=MosqueMembershipRole.ADMIN,
        mosque_memberships__is_active=True,
        is_active=True,
    ).distinct()


def _review_team_users():
    return get_user_model().objects.filter(
        role__in=[
            UserRole.SUPPORT_OFFICER,
            UserRole.PLATFORM_ADMIN,
            UserRole.SUPER_ADMIN,
        ],
        is_active=True,
    ).distinct()


def _record_delivery(notification, channel, recipient, status, provider="", details=""):
    return SupportNotificationDelivery.objects.create(
        notification=notification,
        channel=channel,
        recipient=recipient or "",
        status=status,
        provider=provider,
        details=details or "",
    )


def _send_email(notification, user):
    recipient = (user.email or "").strip()
    if not recipient:
        return _record_delivery(
            notification,
            NotificationChannel.EMAIL,
            "",
            NotificationDeliveryStatus.SKIPPED,
            provider="django-email",
            details="User has no registered email address.",
        )

    try:
        send_mail(
            subject=notification.title,
            message=notification.message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[recipient],
            fail_silently=False,
        )
        return _record_delivery(
            notification,
            NotificationChannel.EMAIL,
            recipient,
            NotificationDeliveryStatus.SENT,
            provider=settings.EMAIL_BACKEND,
        )
    except Exception as exc:
        return _record_delivery(
            notification,
            NotificationChannel.EMAIL,
            recipient,
            NotificationDeliveryStatus.FAILED,
            provider=getattr(settings, "EMAIL_BACKEND", "django-email"),
            details=str(exc),
        )


def _sms_recipient(user, support_request):
    registered_mobile = (user.phone_number or "").strip()
    if registered_mobile:
        return registered_mobile

    if support_request.created_by_id == user.id:
        return (support_request.contact_phone or "").strip()

    return ""


def _send_sms(notification, user):
    recipient = _sms_recipient(user, notification.support_request)
    backend_path = getattr(
        settings,
        "SUPPORT_SMS_BACKEND",
        "support_requests.sms_backends.ConsoleSMSBackend",
    )

    if not recipient:
        return _record_delivery(
            notification,
            NotificationChannel.SMS,
            "",
            NotificationDeliveryStatus.SKIPPED,
            provider=backend_path,
            details="User has no registered mobile number.",
        )

    sms_message = notification.message.replace("\n", " ").strip()
    if len(sms_message) > 320:
        sms_message = sms_message[:317] + "..."

    try:
        backend_class = import_string(backend_path)
        backend = backend_class()
        provider_result = backend.send_message(recipient, sms_message)
        return _record_delivery(
            notification,
            NotificationChannel.SMS,
            recipient,
            NotificationDeliveryStatus.SENT,
            provider=getattr(backend, "provider_name", backend_path),
            details=str(provider_result or ""),
        )
    except Exception as exc:
        return _record_delivery(
            notification,
            NotificationChannel.SMS,
            recipient,
            NotificationDeliveryStatus.FAILED,
            provider=backend_path,
            details=str(exc),
        )


def _create_notification(user, support_request, notification_type, title, message, external=False):
    notification = SupportNotification.objects.create(
        user=user,
        support_request=support_request,
        notification_type=notification_type,
        title=title,
        message=message,
    )

    if external:
        _send_email(notification, user)
        _send_sms(notification, user)

    return notification


def notify_mosque_admins_documents_required(support_request, notes):
    title = f"Additional information required - {support_request.request_no}"
    message = (
        f"{support_request.mosque.name_en}: additional information or documents "
        f"are required for support request {support_request.request_no}. "
        f"Requested by the reviewing administrator: {notes}. "
        "Open your mosque portal, add the requested information/documents, and resubmit the request."
    )

    return [
        _create_notification(
            user,
            support_request,
            SupportNotificationType.DOCUMENTS_REQUIRED,
            title,
            message,
            external=True,
        )
        for user in _mosque_admin_users(support_request)
    ]


def notify_mosque_admins_approved(support_request):
    title = f"Support request approved - {support_request.request_no}"
    amount_text = (
        f" Approved amount: LKR {support_request.approved_amount}."
        if support_request.approved_amount is not None
        else ""
    )
    message = (
        f"{support_request.mosque.name_en}: support request "
        f"{support_request.request_no} has been approved.{amount_text} "
        "Open your mosque portal to view the request status and details."
    )

    return [
        _create_notification(
            user,
            support_request,
            SupportNotificationType.REQUEST_APPROVED,
            title,
            message,
            external=True,
        )
        for user in _mosque_admin_users(support_request)
    ]


def notify_review_team_submission(support_request, resubmitted=False):
    if resubmitted:
        notification_type = SupportNotificationType.REQUEST_RESUBMITTED
        title = f"Support request resubmitted - {support_request.request_no}"
        message = (
            f"{support_request.mosque.name_en} has added the requested information/documents "
            f"and resubmitted support request {support_request.request_no}. "
            "The request is ready for review again."
        )
    else:
        notification_type = SupportNotificationType.REQUEST_SUBMITTED
        title = f"New support request - {support_request.request_no}"
        message = (
            f"{support_request.mosque.name_en} submitted support request "
            f"{support_request.request_no}: {support_request.title}."
        )

    return [
        _create_notification(
            user,
            support_request,
            notification_type,
            title,
            message,
            external=False,
        )
        for user in _review_team_users()
    ]
