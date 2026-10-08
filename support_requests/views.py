from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.models import OTPPurpose, UserRole
from accounts.otp import (
    OTPError,
    attach_challenge_to_session,
    ensure_request_session_key,
    start_otp_challenge,
)
from dashboard.access import role_required
from mosques.models import (
    Mosque,
    MosqueMembership,
    MosqueMembershipRole,
    MosqueStatus,
)

from .access import (
    assert_can_manage_support_request,
    assert_can_view_support_request,
    can_manage_support_request,
    is_support_reviewer,
)
from .forms import (
    NotificationPreferenceForm,
    SupportRequestDocumentForm,
    SupportRequestForm,
    SupportRequestReviewForm,
)
from .models import (
    MosqueSupportRequest,
    NotificationCategory,
    NotificationPreference,
    SupportNotification,
    SupportRequestDocument,
    SupportRequestHistory,
    SupportRequestStatus,
)
from .notifications import (
    notify_mosque_admins_approved,
    notify_mosque_admins_documents_required,
    notify_mosque_admins_support_status,
    notify_review_team_submission,
)


def _request_queryset():
    return MosqueSupportRequest.objects.select_related(
        "mosque",
        "mosque__district",
        "mosque__province",
        "created_by",
        "assigned_to",
        "reviewed_by",
    ).prefetch_related(
        "documents",
        "history__actor",
    )


def _get_request(request_no):
    return get_object_or_404(
        _request_queryset(),
        request_no=request_no,
    )


def _record_history(support_request, from_status, to_status, actor, notes=""):
    SupportRequestHistory.objects.create(
        support_request=support_request,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        notes=notes or "",
    )


@login_required
def my_requests(request):
    if is_support_reviewer(request.user):
        queryset = _request_queryset()
    else:
        mosque_ids = MosqueMembership.objects.filter(
            user=request.user,
            is_active=True,
        ).values_list("mosque_id", flat=True)

        queryset = _request_queryset().filter(
            mosque_id__in=mosque_ids,
        )

    status = request.GET.get("status", "").strip()
    query = request.GET.get("q", "").strip()

    if status:
        queryset = queryset.filter(status=status)

    if query:
        queryset = queryset.filter(
            Q(request_no__icontains=query)
            | Q(title__icontains=query)
            | Q(mosque__name_en__icontains=query)
            | Q(mosque__mosque_id__icontains=query)
        )

    return render(
        request,
        "support_requests/my_requests.html",
        {
            "support_requests": queryset,
            "selected_status": status,
            "query": query,
            "status_choices": SupportRequestStatus.choices,
            "can_create": request.user.role == UserRole.MOSQUE_ADMIN,
        },
    )


@role_required(UserRole.MOSQUE_ADMIN)
def support_request_create(request):
    initial_mosque = None
    mosque_id = request.GET.get("mosque", "").strip()

    if mosque_id:
        initial_mosque = Mosque.objects.filter(
            mosque_id=mosque_id,
            status=MosqueStatus.APPROVED,
        ).first()

    form = SupportRequestForm(
        request.POST or None,
        user=request.user,
        mosque=initial_mosque,
    )

    if request.method == "POST" and form.is_valid():
        support_request = form.save(commit=False)
        support_request.created_by = request.user
        support_request.status = SupportRequestStatus.DRAFT
        support_request.save()

        messages.success(
            request,
            _("Support request draft created. Add supporting documents if needed, then submit it."),
        )
        return redirect(
            "support_requests:detail",
            request_no=support_request.request_no,
        )

    return render(
        request,
        "support_requests/request_form.html",
        {
            "form": form,
            "is_edit": False,
        },
    )


@login_required
def support_request_detail(request, request_no):
    support_request = _get_request(request_no)
    assert_can_view_support_request(request.user, support_request)

    can_manage = can_manage_support_request(request.user, support_request)
    reviewer = is_support_reviewer(request.user)

    return render(
        request,
        "support_requests/request_detail.html",
        {
            "support_request": support_request,
            "can_manage": can_manage,
            "is_reviewer": reviewer,
            "can_edit": can_manage and support_request.is_editable_by_mosque,
            "can_submit": can_manage
            and support_request.status
            in {
                SupportRequestStatus.DRAFT,
                SupportRequestStatus.DOCUMENTS_REQUIRED,
            },
            "can_cancel": can_manage
            and support_request.status
            in {
                SupportRequestStatus.DRAFT,
                SupportRequestStatus.SUBMITTED,
                SupportRequestStatus.DOCUMENTS_REQUIRED,
            },
            "can_add_document": can_manage
            and support_request.status
            not in {
                SupportRequestStatus.COMPLETED,
                SupportRequestStatus.REJECTED,
                SupportRequestStatus.CANCELLED,
            },
            "can_delete_document": can_manage
            and support_request.status
            in {
                SupportRequestStatus.DRAFT,
                SupportRequestStatus.DOCUMENTS_REQUIRED,
            },
        },
    )


@login_required
def support_request_edit(request, request_no):
    support_request = _get_request(request_no)
    assert_can_manage_support_request(request.user, support_request)

    if not support_request.is_editable_by_mosque:
        raise PermissionDenied

    form = SupportRequestForm(
        request.POST or None,
        instance=support_request,
        user=request.user,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Support request details updated."))
        return redirect(
            "support_requests:detail",
            request_no=support_request.request_no,
        )

    return render(
        request,
        "support_requests/request_form.html",
        {
            "form": form,
            "support_request": support_request,
            "is_edit": True,
        },
    )


@login_required
def support_request_submit(request, request_no):
    support_request = _get_request(request_no)
    assert_can_manage_support_request(request.user, support_request)

    if request.method != "POST":
        raise PermissionDenied

    if support_request.status not in {
        SupportRequestStatus.DRAFT,
        SupportRequestStatus.DOCUMENTS_REQUIRED,
    }:
        raise PermissionDenied

    phone_number = (request.user.phone_number or "").strip()
    if not phone_number:
        messages.error(
            request,
            _("Add a registered mobile number to your account before submitting a support request."),
        )
        return redirect(
            "support_requests:detail",
            request_no=support_request.request_no,
        )

    try:
        challenge, delivered, _details = start_otp_challenge(
            user=request.user,
            phone_number=phone_number,
            purpose=OTPPurpose.SUPPORT_SUBMISSION,
            session_key=ensure_request_session_key(request),
            target_reference=support_request.request_no,
        )
    except OTPError as exc:
        messages.error(request, str(exc))
        return redirect(
            "support_requests:detail",
            request_no=support_request.request_no,
        )

    attach_challenge_to_session(request, challenge)

    if delivered:
        messages.info(
            request,
            _("An SMS OTP was sent to your registered mobile number. Verify it to submit the support request."),
        )
    else:
        messages.warning(
            request,
            _("The OTP challenge was created, but SMS delivery failed. You can retry from the verification page."),
        )

    return redirect("accounts:otp_verify")


@login_required
@transaction.atomic
def support_request_cancel(request, request_no):
    support_request = _get_request(request_no)
    assert_can_manage_support_request(request.user, support_request)

    if request.method != "POST":
        raise PermissionDenied

    if support_request.status not in {
        SupportRequestStatus.DRAFT,
        SupportRequestStatus.SUBMITTED,
        SupportRequestStatus.DOCUMENTS_REQUIRED,
    }:
        raise PermissionDenied

    old_status = support_request.status
    support_request.status = SupportRequestStatus.CANCELLED
    support_request.save(update_fields=["status", "updated_at"])

    _record_history(
        support_request,
        old_status,
        SupportRequestStatus.CANCELLED,
        request.user,
        _("Cancelled by mosque administration."),
    )

    messages.success(request, _("Support request cancelled."))
    return redirect(
        "support_requests:detail",
        request_no=support_request.request_no,
    )


@login_required
def document_add(request, request_no):
    support_request = _get_request(request_no)
    assert_can_manage_support_request(request.user, support_request)

    if support_request.status in {
        SupportRequestStatus.COMPLETED,
        SupportRequestStatus.REJECTED,
        SupportRequestStatus.CANCELLED,
    }:
        raise PermissionDenied

    form = SupportRequestDocumentForm(
        request.POST or None,
        request.FILES or None,
    )

    if request.method == "POST" and form.is_valid():
        document = form.save(commit=False)
        document.support_request = support_request
        document.uploaded_by = request.user
        document.save()

        messages.success(request, _("Supporting document uploaded."))
        return redirect(
            "support_requests:detail",
            request_no=support_request.request_no,
        )

    return render(
        request,
        "support_requests/document_form.html",
        {
            "form": form,
            "support_request": support_request,
        },
    )


@login_required
def document_delete(request, request_no, document_id):
    support_request = _get_request(request_no)
    assert_can_manage_support_request(request.user, support_request)

    if support_request.status not in {
        SupportRequestStatus.DRAFT,
        SupportRequestStatus.DOCUMENTS_REQUIRED,
    }:
        raise PermissionDenied

    document = get_object_or_404(
        SupportRequestDocument,
        pk=document_id,
        support_request=support_request,
    )

    if request.method != "POST":
        raise PermissionDenied

    if document.file:
        document.file.delete(save=False)
    document.delete()

    messages.success(request, _("Support request document removed."))
    return redirect(
        "support_requests:detail",
        request_no=support_request.request_no,
    )


@role_required(
    UserRole.SUPPORT_OFFICER,
    UserRole.PLATFORM_ADMIN,
    UserRole.SUPER_ADMIN,
)
def review_queue(request):
    queryset = _request_queryset().exclude(
        status__in=[
            SupportRequestStatus.DRAFT,
            SupportRequestStatus.CANCELLED,
        ]
    )

    status = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()
    query = request.GET.get("q", "").strip()

    if status:
        queryset = queryset.filter(status=status)

    if category:
        queryset = queryset.filter(category=category)

    if query:
        queryset = queryset.filter(
            Q(request_no__icontains=query)
            | Q(title__icontains=query)
            | Q(mosque__name_en__icontains=query)
            | Q(mosque__mosque_id__icontains=query)
            | Q(mosque__district__name_en__icontains=query)
        )

    from .models import SupportCategory

    return render(
        request,
        "support_requests/review_queue.html",
        {
            "support_requests": queryset,
            "selected_status": status,
            "selected_category": category,
            "query": query,
            "status_choices": SupportRequestStatus.choices,
            "category_choices": SupportCategory.choices,
        },
    )


@role_required(
    UserRole.SUPPORT_OFFICER,
    UserRole.PLATFORM_ADMIN,
    UserRole.SUPER_ADMIN,
)
def review_detail(request, request_no):
    support_request = _get_request(request_no)

    form = SupportRequestReviewForm(
        support_request=support_request,
    )

    return render(
        request,
        "support_requests/review_detail.html",
        {
            "support_request": support_request,
            "form": form,
        },
    )


@role_required(
    UserRole.SUPPORT_OFFICER,
    UserRole.PLATFORM_ADMIN,
    UserRole.SUPER_ADMIN,
)
@transaction.atomic
def review_action(request, request_no):
    support_request = _get_request(request_no)

    if request.method != "POST":
        raise PermissionDenied

    form = SupportRequestReviewForm(
        request.POST,
        support_request=support_request,
    )

    if not form.is_valid():
        return render(
            request,
            "support_requests/review_detail.html",
            {
                "support_request": support_request,
                "form": form,
            },
            status=400,
        )

    old_status = support_request.status
    new_status = form.cleaned_data["action"]
    notes = form.cleaned_data.get("notes", "")
    approved_amount = form.cleaned_data.get("approved_amount")

    support_request.status = new_status
    support_request.reviewed_by = request.user
    support_request.reviewed_at = timezone.now()
    support_request.latest_admin_note = notes

    if new_status in {
        SupportRequestStatus.UNDER_REVIEW,
        SupportRequestStatus.APPROVED,
        SupportRequestStatus.IN_PROGRESS,
    }:
        support_request.assigned_to = request.user

    if new_status == SupportRequestStatus.APPROVED:
        support_request.approved_amount = approved_amount

    if new_status == SupportRequestStatus.COMPLETED:
        support_request.completed_at = timezone.now()

    support_request.save()

    _record_history(
        support_request,
        old_status,
        new_status,
        request.user,
        notes,
    )

    if new_status == SupportRequestStatus.DOCUMENTS_REQUIRED:
        notify_mosque_admins_documents_required(
            support_request,
            notes,
            actor=request.user,
        )
    elif new_status == SupportRequestStatus.APPROVED:
        notify_mosque_admins_approved(
            support_request,
            actor=request.user,
        )
    elif new_status in {
        SupportRequestStatus.UNDER_REVIEW,
        SupportRequestStatus.REJECTED,
        SupportRequestStatus.IN_PROGRESS,
        SupportRequestStatus.COMPLETED,
    }:
        notify_mosque_admins_support_status(
            support_request,
            new_status,
            notes=notes,
            actor=request.user,
        )

    messages.success(
        request,
        _("Support request status updated to %(status)s.")
        % {"status": support_request.get_status_display()},
    )

    return redirect(
        "support_requests:review_detail",
        request_no=support_request.request_no,
    )


@login_required
def notification_center(request):
    notifications = SupportNotification.objects.filter(
        user=request.user,
        dashboard_visible=True,
    ).select_related(
        "support_request",
        "support_request__mosque",
        "mosque",
        "actor",
    ).prefetch_related("deliveries")

    category = request.GET.get("category", "").strip()
    state = request.GET.get("state", "").strip()

    if category in NotificationCategory.values:
        notifications = notifications.filter(category=category)

    if state == "unread":
        notifications = notifications.filter(is_read=False)
    elif state == "read":
        notifications = notifications.filter(is_read=True)

    return render(
        request,
        "support_requests/notification_center.html",
        {
            "notifications": notifications[:200],
            "category_choices": NotificationCategory.choices,
            "selected_category": category,
            "selected_state": state,
            "unread_count": SupportNotification.objects.filter(
                user=request.user,
                dashboard_visible=True,
                is_read=False,
            ).count(),
        },
    )


def _open_notification(request, notification_id):
    notification = get_object_or_404(
        SupportNotification,
        pk=notification_id,
        user=request.user,
        dashboard_visible=True,
    )
    notification.mark_read()

    target = (notification.action_url or "").strip()
    if not target.startswith("/"):
        return redirect("dashboard:home")
    return redirect(target)


@login_required
def notification_open(request, notification_id):
    # Backward-compatible Phase 6 route.
    return _open_notification(request, notification_id)


@login_required
def notification_open_global(request, notification_id):
    return _open_notification(request, notification_id)


def _mark_all_read(request, redirect_name):
    if request.method != "POST":
        raise PermissionDenied

    now = timezone.now()
    SupportNotification.objects.filter(
        user=request.user,
        dashboard_visible=True,
        is_read=False,
    ).update(
        is_read=True,
        read_at=now,
    )

    messages.success(request, _("All notifications marked as read."))
    return redirect(redirect_name)


@login_required
def notifications_mark_all_read(request):
    # Backward-compatible Phase 6 route.
    return _mark_all_read(request, "support_requests:notifications")


@login_required
def notifications_mark_all_read_global(request):
    return _mark_all_read(request, "notifications:center")


@login_required
def notification_preferences(request):
    preferences, _created = NotificationPreference.objects.get_or_create(
        user=request.user,
    )
    form = NotificationPreferenceForm(
        request.POST or None,
        instance=preferences,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Notification preferences updated."))
        return redirect("notifications:preferences")

    return render(
        request,
        "support_requests/notification_preferences.html",
        {"form": form},
    )
