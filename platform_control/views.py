from datetime import timedelta

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.models import User, UserRole
from dashboard.access import role_required
from locations.models import (
    District,
    DistrictOfficerAssignment,
    DivisionalSecretariat,
    GNDivision,
    Province,
)
from mosques.models import Mosque, MosqueMembership, MosqueStatus
from support_requests.models import (
    MosqueSupportRequest,
    NotificationChannel,
    NotificationDeliveryStatus,
    SupportNotificationDelivery,
    SupportRequestStatus,
)

from .forms import ControlUserCreateForm, ControlUserUpdateForm


control_required = role_required(
    UserRole.PLATFORM_ADMIN,
    UserRole.SUPER_ADMIN,
)


def _is_super_actor(user):
    return user.is_superuser or user.role == UserRole.SUPER_ADMIN


def _can_manage_user(actor, target):
    if target.is_superuser or target.role == UserRole.SUPER_ADMIN:
        return False

    if (
        actor.role == UserRole.PLATFORM_ADMIN
        and target.role == UserRole.PLATFORM_ADMIN
    ):
        return False

    return True


def _visible_users(actor):
    queryset = User.objects.all()

    if not _is_super_actor(actor):
        queryset = queryset.exclude(
            Q(is_superuser=True) | Q(role=UserRole.SUPER_ADMIN)
        )

    return queryset.order_by("username")


@control_required
def overview(request):
    support_open_statuses = [
        SupportRequestStatus.SUBMITTED,
        SupportRequestStatus.UNDER_REVIEW,
        SupportRequestStatus.DOCUMENTS_REQUIRED,
        SupportRequestStatus.APPROVED,
        SupportRequestStatus.IN_PROGRESS,
    ]

    seven_days_ago = timezone.now() - timedelta(days=7)

    role_counts = {
        row["role"]: row["total"]
        for row in User.objects.filter(is_active=True)
        .values("role")
        .annotate(total=Count("id"))
    }

    context = {
        "user_count": User.objects.filter(is_active=True).count(),
        "mosque_pending_count": Mosque.objects.filter(
            status=MosqueStatus.SUBMITTED,
        ).count(),
        "mosque_approved_count": Mosque.objects.filter(
            status=MosqueStatus.APPROVED,
        ).count(),
        "support_open_count": MosqueSupportRequest.objects.filter(
            status__in=support_open_statuses,
        ).count(),
        "support_documents_required_count": MosqueSupportRequest.objects.filter(
            status=SupportRequestStatus.DOCUMENTS_REQUIRED,
        ).count(),
        "support_completed_count": MosqueSupportRequest.objects.filter(
            status=SupportRequestStatus.COMPLETED,
        ).count(),
        "delivery_failed_count": SupportNotificationDelivery.objects.filter(
            status=NotificationDeliveryStatus.FAILED,
            attempted_at__gte=seven_days_ago,
        ).count(),
        "province_count": Province.objects.count(),
        "district_count": District.objects.count(),
        "ds_count": DivisionalSecretariat.objects.count(),
        "gn_count": GNDivision.objects.count(),
        "district_officer_assignment_count": DistrictOfficerAssignment.objects.filter(
            is_active=True,
        ).count(),
        "role_counts": role_counts,
        "recent_mosques": Mosque.objects.select_related(
            "district",
            "created_by",
        ).order_by("-created_at")[:6],
        "recent_support_requests": MosqueSupportRequest.objects.select_related(
            "mosque",
            "assigned_to",
        ).order_by("-updated_at")[:6],
        "recent_delivery_failures": SupportNotificationDelivery.objects.filter(
            status=NotificationDeliveryStatus.FAILED,
        ).select_related(
            "notification",
            "notification__support_request",
            "notification__user",
        )[:6],
    }

    return render(
        request,
        "platform_control/overview.html",
        context,
    )


@control_required
def user_list(request):
    queryset = _visible_users(request.user)

    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()

    if query:
        queryset = queryset.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone_number__icontains=query)
        )

    if role:
        queryset = queryset.filter(role=role)

    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)

    role_choices = list(UserRole.choices)
    if not _is_super_actor(request.user):
        role_choices = [
            item
            for item in role_choices
            if item[0] != UserRole.SUPER_ADMIN
        ]

    return render(
        request,
        "platform_control/user_list.html",
        {
            "users": queryset,
            "query": query,
            "selected_role": role,
            "selected_status": status,
            "role_choices": role_choices,
        },
    )


@control_required
def user_create(request):
    form = ControlUserCreateForm(
        request.POST or None,
        actor=request.user,
    )

    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(
            request,
            _("User %(username)s created successfully.")
            % {"username": user.username},
        )
        return redirect(
            "platform_control:user_detail",
            user_id=user.pk,
        )

    return render(
        request,
        "platform_control/user_form.html",
        {
            "form": form,
            "is_edit": False,
        },
    )


@control_required
def user_detail(request, user_id):
    target = get_object_or_404(
        _visible_users(request.user),
        pk=user_id,
    )

    memberships = MosqueMembership.objects.filter(
        user=target,
    ).select_related(
        "mosque",
    )

    district_assignment = DistrictOfficerAssignment.objects.filter(
        user=target,
    ).select_related(
        "district",
        "district__province",
    ).first()

    return render(
        request,
        "platform_control/user_detail.html",
        {
            "target_user": target,
            "memberships": memberships,
            "district_assignment": district_assignment,
            "created_support_count": MosqueSupportRequest.objects.filter(
                created_by=target,
            ).count(),
            "assigned_support_count": MosqueSupportRequest.objects.filter(
                assigned_to=target,
            ).count(),
            "can_edit": _can_manage_user(request.user, target),
        },
    )


@control_required
def user_edit(request, user_id):
    target = get_object_or_404(
        _visible_users(request.user),
        pk=user_id,
    )

    if not _can_manage_user(request.user, target):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    form = ControlUserUpdateForm(
        request.POST or None,
        instance=target,
        actor=request.user,
    )

    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(
            request,
            _("User %(username)s updated successfully.")
            % {"username": user.username},
        )
        return redirect(
            "platform_control:user_detail",
            user_id=user.pk,
        )

    return render(
        request,
        "platform_control/user_form.html",
        {
            "form": form,
            "is_edit": True,
            "target_user": target,
        },
    )


@control_required
def notification_delivery_monitor(request):
    deliveries = SupportNotificationDelivery.objects.select_related(
        "notification",
        "notification__support_request",
        "notification__support_request__mosque",
        "notification__user",
    )

    status = request.GET.get("status", "").strip()
    channel = request.GET.get("channel", "").strip()
    query = request.GET.get("q", "").strip()

    if status:
        deliveries = deliveries.filter(status=status)

    if channel:
        deliveries = deliveries.filter(channel=channel)

    if query:
        deliveries = deliveries.filter(
            Q(recipient__icontains=query)
            | Q(notification__title__icontains=query)
            | Q(notification__support_request__request_no__icontains=query)
            | Q(notification__support_request__mosque__name_en__icontains=query)
            | Q(notification__user__username__icontains=query)
        )

    return render(
        request,
        "platform_control/notification_delivery_monitor.html",
        {
            "deliveries": deliveries[:250],
            "selected_status": status,
            "selected_channel": channel,
            "query": query,
            "status_choices": NotificationDeliveryStatus.choices,
            "channel_choices": NotificationChannel.choices,
            "sent_count": SupportNotificationDelivery.objects.filter(
                status=NotificationDeliveryStatus.SENT,
            ).count(),
            "failed_count": SupportNotificationDelivery.objects.filter(
                status=NotificationDeliveryStatus.FAILED,
            ).count(),
            "skipped_count": SupportNotificationDelivery.objects.filter(
                status=NotificationDeliveryStatus.SKIPPED,
            ).count(),
        },
    )
