from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import translation
from django.utils.module_loading import import_string

from accounts.models import UserRole
from mosques.models import MosqueMembership, MosqueMembershipRole

from .models import (
    NotificationCategory,
    NotificationChannel,
    NotificationDeliveryStatus,
    NotificationPreference,
    NotificationPriority,
    SupportNotification,
    SupportNotificationDelivery,
    SupportNotificationType,
    SupportRequestStatus,
)


SUPPORTED_LANGUAGES = {"en", "ta", "ar"}


ROLE_LABELS = {
    "MOSQUE_ADMIN": {"en": "Mosque Admin", "ta": "பள்ளிவாசல் நிர்வாகி", "ar": "مدير المسجد"},
    "MOSQUE_STAFF": {"en": "Mosque Staff", "ta": "பள்ளிவாசல் பணியாளர்", "ar": "موظف المسجد"},
    "DISTRICT_OFFICER": {"en": "District Officer", "ta": "மாவட்ட அலுவலர்", "ar": "مسؤول المنطقة"},
    "SUPPORT_OFFICER": {"en": "Support Officer", "ta": "ஆதரவு அலுவலர்", "ar": "مسؤول الدعم"},
    "PLATFORM_ADMIN": {"en": "Platform Admin", "ta": "பிளாட்ஃபாரம் நிர்வாகி", "ar": "مدير المنصة"},
    "SUPER_ADMIN": {"en": "Super Admin", "ta": "முதன்மை நிர்வாகி", "ar": "المدير الأعلى"},
    "ADMIN": {"en": "Mosque Admin", "ta": "பள்ளிவாசல் நிர்வாகி", "ar": "مدير المسجد"},
    "STAFF": {"en": "Mosque Staff", "ta": "பள்ளிவாசல் பணியாளர்", "ar": "موظف المسجد"},
}


TEMPLATES = {
    SupportNotificationType.REQUEST_SUBMITTED: {
        "en": ("New support request - {request_no}", "{mosque} submitted support request {request_no}: {title}."),
        "ta": ("புதிய ஆதரவு கோரிக்கை - {request_no}", "{mosque} பள்ளிவாசல் {request_no} என்ற ஆதரவு கோரிக்கையை சமர்ப்பித்துள்ளது: {title}."),
        "ar": ("طلب دعم جديد - {request_no}", "قدّم مسجد {mosque} طلب الدعم {request_no}: {title}."),
    },
    SupportNotificationType.REQUEST_RESUBMITTED: {
        "en": ("Support request resubmitted - {request_no}", "{mosque} added the requested information/documents and resubmitted {request_no}. It is ready for review again."),
        "ta": ("ஆதரவு கோரிக்கை மீண்டும் சமர்ப்பிக்கப்பட்டது - {request_no}", "{mosque} கேட்ட தகவல்/ஆவணங்களைச் சேர்த்து {request_no} கோரிக்கையை மீண்டும் சமர்ப்பித்துள்ளது. இது மறுபரிசீலனைக்கு தயாராக உள்ளது."),
        "ar": ("تمت إعادة تقديم طلب الدعم - {request_no}", "أضاف مسجد {mosque} المعلومات/المستندات المطلوبة وأعاد تقديم {request_no}. الطلب جاهز للمراجعة مرة أخرى."),
    },
    SupportNotificationType.REQUEST_UNDER_REVIEW: {
        "en": ("Support request under review - {request_no}", "Your support request {request_no} ({mosque}) is now under review by the administration."),
        "ta": ("ஆதரவு கோரிக்கை பரிசீலனையில் உள்ளது - {request_no}", "உங்கள் {request_no} ({mosque}) ஆதரவு கோரிக்கை தற்போது நிர்வாகத்தால் பரிசீலிக்கப்படுகிறது."),
        "ar": ("طلب الدعم قيد المراجعة - {request_no}", "طلب الدعم الخاص بكم {request_no} ({mosque}) قيد المراجعة الآن من قبل الإدارة."),
    },
    SupportNotificationType.DOCUMENTS_REQUIRED: {
        "en": ("Additional information required - {request_no}", "Additional information or documents are required for {request_no} ({mosque}). Administrator note: {notes}. Add the requested information/documents and resubmit."),
        "ta": ("கூடுதல் தகவல் தேவை - {request_no}", "{request_no} ({mosque}) கோரிக்கைக்கு கூடுதல் தகவல் அல்லது ஆவணங்கள் தேவை. நிர்வாகக் குறிப்பு: {notes}. தேவையான தகவல்/ஆவணங்களைச் சேர்த்து மீண்டும் சமர்ப்பிக்கவும்."),
        "ar": ("معلومات إضافية مطلوبة - {request_no}", "يلزم تقديم معلومات أو مستندات إضافية للطلب {request_no} ({mosque}). ملاحظة الإدارة: {notes}. أضف المطلوب ثم أعد تقديم الطلب."),
    },
    SupportNotificationType.REQUEST_APPROVED: {
        "en": ("Support request approved - {request_no}", "Your mosque support request {request_no} ({mosque}) has been approved. Approved amount: LKR {approved_amount}."),
        "ta": ("ஆதரவு கோரிக்கை அங்கீகரிக்கப்பட்டது - {request_no}", "உங்கள் {request_no} ({mosque}) ஆதரவு கோரிக்கை அங்கீகரிக்கப்பட்டுள்ளது. அங்கீகரிக்கப்பட்ட தொகை: LKR {approved_amount}."),
        "ar": ("تمت الموافقة على طلب الدعم - {request_no}", "تمت الموافقة على طلب دعم مسجدكم {request_no} ({mosque}). المبلغ المعتمد: LKR {approved_amount}."),
    },
    SupportNotificationType.REQUEST_REJECTED: {
        "en": ("Support request rejected - {request_no}", "Support request {request_no} ({mosque}) was rejected. Administrator note: {notes}"),
        "ta": ("ஆதரவு கோரிக்கை நிராகரிக்கப்பட்டது - {request_no}", "{request_no} ({mosque}) ஆதரவு கோரிக்கை நிராகரிக்கப்பட்டது. நிர்வாகக் குறிப்பு: {notes}"),
        "ar": ("تم رفض طلب الدعم - {request_no}", "تم رفض طلب الدعم {request_no} ({mosque}). ملاحظة الإدارة: {notes}"),
    },
    SupportNotificationType.REQUEST_IN_PROGRESS: {
        "en": ("Support request in progress - {request_no}", "Support request {request_no} ({mosque}) is now in progress."),
        "ta": ("ஆதரவு கோரிக்கை செயல்பாட்டில் உள்ளது - {request_no}", "{request_no} ({mosque}) ஆதரவு கோரிக்கை தற்போது செயல்பாட்டில் உள்ளது."),
        "ar": ("طلب الدعم قيد التنفيذ - {request_no}", "طلب الدعم {request_no} ({mosque}) قيد التنفيذ الآن."),
    },
    SupportNotificationType.REQUEST_COMPLETED: {
        "en": ("Support request completed - {request_no}", "Support request {request_no} ({mosque}) has been marked completed."),
        "ta": ("ஆதரவு கோரிக்கை நிறைவு பெற்றது - {request_no}", "{request_no} ({mosque}) ஆதரவு கோரிக்கை நிறைவு பெற்றதாக குறிக்கப்பட்டுள்ளது."),
        "ar": ("اكتمل طلب الدعم - {request_no}", "تم وضع علامة مكتمل على طلب الدعم {request_no} ({mosque})."),
    },
    SupportNotificationType.MOSQUE_SUBMITTED: {
        "en": ("Mosque registration submitted - {mosque_id}", "{mosque} ({mosque_id}) has been submitted for Platform Admin approval."),
        "ta": ("பள்ளிவாசல் பதிவு சமர்ப்பிக்கப்பட்டது - {mosque_id}", "{mosque} ({mosque_id}) பிளாட்ஃபாரம் நிர்வாகி அங்கீகாரத்திற்காக சமர்ப்பிக்கப்பட்டுள்ளது."),
        "ar": ("تم تقديم تسجيل المسجد - {mosque_id}", "تم تقديم {mosque} ({mosque_id}) لموافقة إدارة المنصة."),
    },
    SupportNotificationType.MOSQUE_APPROVED: {
        "en": ("Mosque registration approved - {mosque_id}", "{mosque} ({mosque_id}) has been approved and is now eligible for the public Mosque Directory and mosque portal."),
        "ta": ("பள்ளிவாசல் பதிவு அங்கீகரிக்கப்பட்டது - {mosque_id}", "{mosque} ({mosque_id}) அங்கீகரிக்கப்பட்டுள்ளது. இப்போது பள்ளிவாசல் அடைவு மற்றும் பள்ளிவாசல் போர்டல் பயன்பாட்டிற்கு தகுதி பெற்றுள்ளது."),
        "ar": ("تمت الموافقة على تسجيل المسجد - {mosque_id}", "تمت الموافقة على {mosque} ({mosque_id}) وأصبح مؤهلاً للظهور في دليل المساجد واستخدام بوابة المسجد."),
    },
    SupportNotificationType.MOSQUE_REJECTED: {
        "en": ("Mosque registration rejected - {mosque_id}", "{mosque} ({mosque_id}) was rejected. Administrator note: {notes}"),
        "ta": ("பள்ளிவாசல் பதிவு நிராகரிக்கப்பட்டது - {mosque_id}", "{mosque} ({mosque_id}) பதிவு நிராகரிக்கப்பட்டது. நிர்வாகக் குறிப்பு: {notes}"),
        "ar": ("تم رفض تسجيل المسجد - {mosque_id}", "تم رفض تسجيل {mosque} ({mosque_id}). ملاحظة الإدارة: {notes}"),
    },
    SupportNotificationType.MOSQUE_ACCESS_ADDED: {
        "en": ("Mosque portal access added", "You have been added to {mosque} as {role}. You can now access the mosque portal according to your role."),
        "ta": ("பள்ளிவாசல் போர்டல் அணுகல் சேர்க்கப்பட்டது", "{mosque} பள்ளிவாசலுக்கு {role} ஆக நீங்கள் சேர்க்கப்பட்டுள்ளீர்கள். உங்கள் பங்கிற்கேற்ப போர்டலை அணுகலாம்."),
        "ar": ("تمت إضافة صلاحية بوابة المسجد", "تمت إضافتك إلى {mosque} بصلاحية {role}. يمكنك الآن الدخول إلى بوابة المسجد وفقاً لدورك."),
    },
    SupportNotificationType.MOSQUE_ACCESS_REMOVED: {
        "en": ("Mosque portal access removed", "Your access to {mosque} as {role} has been removed."),
        "ta": ("பள்ளிவாசல் போர்டல் அணுகல் நீக்கப்பட்டது", "{mosque} பள்ளிவாசலுக்கான உங்கள் {role} அணுகல் நீக்கப்பட்டுள்ளது."),
        "ar": ("تمت إزالة صلاحية بوابة المسجد", "تمت إزالة صلاحيتك في {mosque} كـ {role}."),
    },
    SupportNotificationType.ACCOUNT_CREATED: {
        "en": ("Your platform account is ready", "A {role} account has been created for you on the Sri Lanka Mosque Platform. Username: {username}. Sign in using the password provided securely by your administrator."),
        "ta": ("உங்கள் பிளாட்ஃபாரம் கணக்கு தயார்", "இலங்கை பள்ளிவாசல் பிளாட்ஃபாரத்தில் உங்களுக்கு {role} கணக்கு உருவாக்கப்பட்டுள்ளது. பயனர் பெயர்: {username}. நிர்வாகி பாதுகாப்பாக வழங்கிய கடவுச்சொல்லைப் பயன்படுத்தி உள்நுழையவும்."),
        "ar": ("حساب المنصة الخاص بك جاهز", "تم إنشاء حساب بدور {role} لك في منصة مساجد سريلانكا. اسم المستخدم: {username}. سجّل الدخول باستخدام كلمة المرور التي سلّمها لك المسؤول بشكل آمن."),
    },
    SupportNotificationType.ACCOUNT_ACTIVATED: {
        "en": ("Account activated", "Your Sri Lanka Mosque Platform account has been activated."),
        "ta": ("கணக்கு செயல்படுத்தப்பட்டது", "உங்கள் இலங்கை பள்ளிவாசல் பிளாட்ஃபாரம் கணக்கு செயல்படுத்தப்பட்டுள்ளது."),
        "ar": ("تم تفعيل الحساب", "تم تفعيل حسابك في منصة مساجد سريلانكا."),
    },
    SupportNotificationType.ACCOUNT_DEACTIVATED: {
        "en": ("Account deactivated", "Your Sri Lanka Mosque Platform account has been deactivated. Contact the Platform Administrator if you need assistance."),
        "ta": ("கணக்கு செயலிழக்கச் செய்யப்பட்டது", "உங்கள் இலங்கை பள்ளிவாசல் பிளாட்ஃபாரம் கணக்கு செயலிழக்கச் செய்யப்பட்டுள்ளது. உதவி தேவைப்பட்டால் பிளாட்ஃபாரம் நிர்வாகியை தொடர்பு கொள்ளவும்."),
        "ar": ("تم تعطيل الحساب", "تم تعطيل حسابك في منصة مساجد سريلانكا. تواصل مع إدارة المنصة إذا احتجت إلى مساعدة."),
    },
    SupportNotificationType.ACCOUNT_ROLE_CHANGED: {
        "en": ("Account role updated", "Your platform role has changed from {old_role} to {new_role}."),
        "ta": ("கணக்கு பங்கு மாற்றப்பட்டது", "உங்கள் பிளாட்ஃபாரம் பங்கு {old_role} இலிருந்து {new_role} ஆக மாற்றப்பட்டுள்ளது."),
        "ar": ("تم تحديث دور الحساب", "تم تغيير دورك في المنصة من {old_role} إلى {new_role}."),
    },
    SupportNotificationType.DISTRICT_ASSIGNED: {
        "en": ("District assignment updated", "You have been assigned to {district}, {province} as a District Officer."),
        "ta": ("மாவட்ட ஒதுக்கீடு புதுப்பிக்கப்பட்டது", "மாவட்ட அலுவலராக {district}, {province} உங்களுக்கு ஒதுக்கப்பட்டுள்ளது."),
        "ar": ("تم تحديث تعيين المنطقة", "تم تعيينك مسؤول منطقة لـ {district}، {province}."),
    },
    SupportNotificationType.DISTRICT_ASSIGNMENT_REMOVED: {
        "en": ("District assignment removed", "Your District Officer assignment for {district}, {province} has been removed."),
        "ta": ("மாவட்ட ஒதுக்கீடு நீக்கப்பட்டது", "{district}, {province} மாவட்ட அலுவலர் ஒதுக்கீடு நீக்கப்பட்டுள்ளது."),
        "ar": ("تمت إزالة تعيين المنطقة", "تمت إزالة تعيينك كمسؤول منطقة لـ {district}، {province}."),
    },
}


def _language_for_user(user):
    language = (getattr(user, "preferred_language", "en") or "en").split("-")[0]
    return language if language in SUPPORTED_LANGUAGES else "en"


def _render_message(user, notification_type, context):
    language = _language_for_user(user)
    templates = TEMPLATES.get(notification_type, {}).get(language)
    if not templates:
        templates = TEMPLATES.get(notification_type, {}).get("en")
    if not templates:
        return notification_type, str(context), language

    title_template, message_template = templates
    safe_context = {key: ("" if value is None else value) for key, value in context.items()}
    return (
        title_template.format(**safe_context),
        message_template.format(**safe_context),
        language,
    )


def _localized_reverse(user, viewname, kwargs=None):
    language = _language_for_user(user)
    with translation.override(language):
        return reverse(viewname, kwargs=kwargs or {})


def _preferences(user):
    preferences, _created = NotificationPreference.objects.get_or_create(user=user)
    return preferences


def _record_delivery(
    notification,
    channel,
    recipient,
    status,
    provider="",
    details="",
    retry_of=None,
    retried_by=None,
):
    return SupportNotificationDelivery.objects.create(
        notification=notification,
        channel=channel,
        recipient=recipient or "",
        status=status,
        provider=provider,
        details=details or "",
        retry_of=retry_of,
        retried_by=retried_by,
    )


def _send_email(notification, user, retry_of=None, retried_by=None):
    recipient = (user.email or "").strip()
    if not recipient:
        return _record_delivery(
            notification,
            NotificationChannel.EMAIL,
            "",
            NotificationDeliveryStatus.SKIPPED,
            provider="django-email",
            details="User has no registered email address.",
            retry_of=retry_of,
            retried_by=retried_by,
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
            retry_of=retry_of,
            retried_by=retried_by,
        )
    except Exception as exc:
        return _record_delivery(
            notification,
            NotificationChannel.EMAIL,
            recipient,
            NotificationDeliveryStatus.FAILED,
            provider=getattr(settings, "EMAIL_BACKEND", "django-email"),
            details=str(exc),
            retry_of=retry_of,
            retried_by=retried_by,
        )


def _sms_recipient(user, notification):
    registered_mobile = (getattr(user, "phone_number", "") or "").strip()
    if registered_mobile:
        return registered_mobile

    if (
        notification.support_request_id
        and notification.support_request.created_by_id == user.id
    ):
        return (notification.support_request.contact_phone or "").strip()

    return ""


def _send_sms(notification, user, retry_of=None, retried_by=None):
    recipient = _sms_recipient(user, notification)
    backend_path = getattr(
        settings,
        "NOTIFICATION_SMS_BACKEND",
        getattr(
            settings,
            "SUPPORT_SMS_BACKEND",
            "support_requests.sms_backends.ConsoleSMSBackend",
        ),
    )

    if not recipient:
        return _record_delivery(
            notification,
            NotificationChannel.SMS,
            "",
            NotificationDeliveryStatus.SKIPPED,
            provider=backend_path,
            details="User has no registered mobile number.",
            retry_of=retry_of,
            retried_by=retried_by,
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
            retry_of=retry_of,
            retried_by=retried_by,
        )
    except Exception as exc:
        return _record_delivery(
            notification,
            NotificationChannel.SMS,
            recipient,
            NotificationDeliveryStatus.FAILED,
            provider=backend_path,
            details=str(exc),
            retry_of=retry_of,
            retried_by=retried_by,
        )


def create_platform_notification(
    user,
    notification_type,
    category,
    context,
    *,
    support_request=None,
    mosque=None,
    actor=None,
    action_view=None,
    action_kwargs=None,
    source_label="",
    priority=NotificationPriority.NORMAL,
    external=True,
    force_sms=False,
):
    if not user or not user.pk:
        return None

    preferences = _preferences(user)
    category_enabled = preferences.category_enabled(category)
    if not category_enabled and not force_sms:
        return None

    title, message, language = _render_message(user, notification_type, context)
    action_url = ""
    if action_view:
        action_url = _localized_reverse(user, action_view, kwargs=action_kwargs)

    notification = SupportNotification.objects.create(
        user=user,
        support_request=support_request,
        mosque=mosque or (support_request.mosque if support_request else None),
        actor=actor,
        notification_type=notification_type,
        category=category,
        priority=priority,
        title=title,
        message=message,
        action_url=action_url,
        source_label=source_label,
        language_code=language,
        dashboard_visible=preferences.dashboard_enabled and category_enabled,
        is_read=not (preferences.dashboard_enabled and category_enabled),
    )

    if external:
        if preferences.email_enabled and category_enabled:
            _send_email(notification, user)
        if (preferences.sms_enabled and category_enabled) or force_sms:
            _send_sms(notification, user)

    return notification


def retry_delivery(delivery, actor=None):
    notification = delivery.notification
    user = notification.user
    if delivery.channel == NotificationChannel.EMAIL:
        return _send_email(
            notification,
            user,
            retry_of=delivery,
            retried_by=actor,
        )
    if delivery.channel == NotificationChannel.SMS:
        return _send_sms(
            notification,
            user,
            retry_of=delivery,
            retried_by=actor,
        )
    raise ValueError("Unsupported notification channel")


def _mosque_admin_users(mosque):
    return get_user_model().objects.filter(
        mosque_memberships__mosque=mosque,
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


def _platform_admin_users():
    return get_user_model().objects.filter(
        role__in=[UserRole.PLATFORM_ADMIN, UserRole.SUPER_ADMIN],
        is_active=True,
    ).distinct()


def notify_review_team_submission(support_request, resubmitted=False, actor=None):
    notification_type = (
        SupportNotificationType.REQUEST_RESUBMITTED
        if resubmitted
        else SupportNotificationType.REQUEST_SUBMITTED
    )
    context = {
        "request_no": support_request.request_no,
        "mosque": support_request.mosque.name_en,
        "title": support_request.title,
    }
    return [
        create_platform_notification(
            user,
            notification_type,
            NotificationCategory.SUPPORT,
            context,
            support_request=support_request,
            actor=actor,
            action_view="support_requests:review_detail",
            action_kwargs={"request_no": support_request.request_no},
            source_label=support_request.request_no,
            priority=NotificationPriority.HIGH if resubmitted else NotificationPriority.NORMAL,
            external=True,
        )
        for user in _review_team_users()
    ]


def notify_mosque_admins_documents_required(support_request, notes, actor=None):
    context = {
        "request_no": support_request.request_no,
        "mosque": support_request.mosque.name_en,
        "notes": notes,
    }
    return [
        create_platform_notification(
            user,
            SupportNotificationType.DOCUMENTS_REQUIRED,
            NotificationCategory.SUPPORT,
            context,
            support_request=support_request,
            actor=actor,
            action_view="support_requests:detail",
            action_kwargs={"request_no": support_request.request_no},
            source_label=support_request.request_no,
            priority=NotificationPriority.HIGH,
            external=True,
            force_sms=True,
        )
        for user in _mosque_admin_users(support_request.mosque)
    ]


def notify_mosque_admins_approved(support_request, actor=None):
    context = {
        "request_no": support_request.request_no,
        "mosque": support_request.mosque.name_en,
        "approved_amount": (
            support_request.approved_amount
            if support_request.approved_amount is not None
            else "—"
        ),
    }
    return [
        create_platform_notification(
            user,
            SupportNotificationType.REQUEST_APPROVED,
            NotificationCategory.SUPPORT,
            context,
            support_request=support_request,
            actor=actor,
            action_view="support_requests:detail",
            action_kwargs={"request_no": support_request.request_no},
            source_label=support_request.request_no,
            priority=NotificationPriority.HIGH,
            external=True,
            force_sms=True,
        )
        for user in _mosque_admin_users(support_request.mosque)
    ]


def notify_mosque_admins_support_status(support_request, new_status, notes="", actor=None):
    type_map = {
        SupportRequestStatus.UNDER_REVIEW: SupportNotificationType.REQUEST_UNDER_REVIEW,
        SupportRequestStatus.REJECTED: SupportNotificationType.REQUEST_REJECTED,
        SupportRequestStatus.IN_PROGRESS: SupportNotificationType.REQUEST_IN_PROGRESS,
        SupportRequestStatus.COMPLETED: SupportNotificationType.REQUEST_COMPLETED,
    }
    notification_type = type_map.get(new_status)
    if not notification_type:
        return []

    context = {
        "request_no": support_request.request_no,
        "mosque": support_request.mosque.name_en,
        "notes": notes or "—",
    }
    return [
        create_platform_notification(
            user,
            notification_type,
            NotificationCategory.SUPPORT,
            context,
            support_request=support_request,
            actor=actor,
            action_view="support_requests:detail",
            action_kwargs={"request_no": support_request.request_no},
            source_label=support_request.request_no,
            priority=(
                NotificationPriority.HIGH
                if new_status == SupportRequestStatus.REJECTED
                else NotificationPriority.NORMAL
            ),
            external=True,
            force_sms=True,
        )
        for user in _mosque_admin_users(support_request.mosque)
    ]


def notify_platform_mosque_submitted(mosque, actor=None):
    context = {
        "mosque": mosque.name_en,
        "mosque_id": mosque.mosque_id,
    }
    return [
        create_platform_notification(
            user,
            SupportNotificationType.MOSQUE_SUBMITTED,
            NotificationCategory.MOSQUE,
            context,
            mosque=mosque,
            actor=actor,
            action_view="mosques:review_detail",
            action_kwargs={"mosque_id": mosque.mosque_id},
            source_label=mosque.mosque_id,
            priority=NotificationPriority.HIGH,
            external=True,
        )
        for user in _platform_admin_users()
    ]


def notify_mosque_admins_registration_decision(mosque, approved, notes="", actor=None):
    notification_type = (
        SupportNotificationType.MOSQUE_APPROVED
        if approved
        else SupportNotificationType.MOSQUE_REJECTED
    )
    context = {
        "mosque": mosque.name_en,
        "mosque_id": mosque.mosque_id,
        "notes": notes or "—",
    }
    return [
        create_platform_notification(
            user,
            notification_type,
            NotificationCategory.MOSQUE,
            context,
            mosque=mosque,
            actor=actor,
            action_view=("mosques:portal" if approved else "mosques:detail"),
            action_kwargs={"mosque_id": mosque.mosque_id},
            source_label=mosque.mosque_id,
            priority=NotificationPriority.HIGH,
            external=True,
            force_sms=True,
        )
        for user in _mosque_admin_users(mosque)
    ]


def notify_mosque_access(user, mosque, role_code, added=True, actor=None):
    notification_type = (
        SupportNotificationType.MOSQUE_ACCESS_ADDED
        if added
        else SupportNotificationType.MOSQUE_ACCESS_REMOVED
    )
    language = _language_for_user(user)
    context = {
        "mosque": mosque.get_localized_name(language) if hasattr(mosque, "get_localized_name") else mosque.name_en,
        "role": ROLE_LABELS.get(role_code, {}).get(language, role_code),
    }
    return create_platform_notification(
        user,
        notification_type,
        NotificationCategory.ACCESS,
        context,
        mosque=mosque,
        actor=actor,
        action_view=("mosques:portal" if added and mosque.is_public else "dashboard:home"),
        action_kwargs={"mosque_id": mosque.mosque_id} if added and mosque.is_public else {},
        source_label=mosque.mosque_id,
        external=True,
    )


def notify_account_created(user, actor=None):
    language = _language_for_user(user)
    context = {
        "role": ROLE_LABELS.get(user.role, {}).get(language, user.role),
        "username": user.username,
    }
    return create_platform_notification(
        user,
        SupportNotificationType.ACCOUNT_CREATED,
        NotificationCategory.ACCOUNT,
        context,
        actor=actor,
        action_view="accounts:login",
        source_label=user.username,
        external=True,
    )


def notify_account_status_changed(user, is_active, actor=None):
    notification_type = (
        SupportNotificationType.ACCOUNT_ACTIVATED
        if is_active
        else SupportNotificationType.ACCOUNT_DEACTIVATED
    )
    return create_platform_notification(
        user,
        notification_type,
        NotificationCategory.ACCOUNT,
        {},
        actor=actor,
        action_view="accounts:login" if is_active else None,
        source_label=user.username,
        priority=NotificationPriority.HIGH,
        external=True,
    )


def notify_account_role_changed(user, old_role, new_role, actor=None):
    language = _language_for_user(user)
    context = {
        "old_role": ROLE_LABELS.get(old_role, {}).get(language, old_role),
        "new_role": ROLE_LABELS.get(new_role, {}).get(language, new_role),
    }
    return create_platform_notification(
        user,
        SupportNotificationType.ACCOUNT_ROLE_CHANGED,
        NotificationCategory.ACCOUNT,
        context,
        actor=actor,
        action_view="dashboard:home",
        source_label=user.username,
        external=True,
    )


def notify_district_assignment(user, district, added=True, actor=None):
    notification_type = (
        SupportNotificationType.DISTRICT_ASSIGNED
        if added
        else SupportNotificationType.DISTRICT_ASSIGNMENT_REMOVED
    )
    language = _language_for_user(user)
    context = {
        "district": district.get_localized_name(language),
        "province": district.province.get_localized_name(language),
    }
    return create_platform_notification(
        user,
        notification_type,
        NotificationCategory.ASSIGNMENT,
        context,
        actor=actor,
        action_view="dashboard:home",
        source_label=district.name_en,
        priority=NotificationPriority.HIGH,
        external=True,
    )
