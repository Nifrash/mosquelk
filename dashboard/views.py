from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from accounts.models import UserRole
from locations.models import DistrictOfficerAssignment
from mosques.models import MosqueMembership, MosqueOperationalProfile, MosqueStatus
from support_requests.models import (
    MosqueSupportRequest,
    SupportNotification,
    SupportRequestStatus,
)
from .access import role_required


ROLE_ROUTES = {
    UserRole.MOSQUE_ADMIN: "dashboard:mosque_admin",
    UserRole.MOSQUE_STAFF: "dashboard:mosque_staff",
    UserRole.DISTRICT_OFFICER: "dashboard:district_officer",
    UserRole.SUPPORT_OFFICER: "dashboard:support_officer",
    UserRole.PLATFORM_ADMIN: "dashboard:platform_admin",
    UserRole.SUPER_ADMIN: "dashboard:super_admin",
}


@login_required
def dashboard_home(request):
    if request.user.is_superuser:
        return redirect("dashboard:super_admin")
    return redirect(ROLE_ROUTES.get(request.user.role, "accounts:profile"))


def _render_dashboard(
    request,
    title,
    description,
    modules,
    quick_actions=None,
    extra_context=None,
):
    notifications = SupportNotification.objects.filter(
        user=request.user,
        dashboard_visible=True,
    ).select_related(
        "support_request",
        "support_request__mosque",
        "mosque",
    )[:5]

    unread_notification_count = SupportNotification.objects.filter(
        user=request.user,
        dashboard_visible=True,
        is_read=False,
    ).count()

    context = {
        "dashboard_title": title,
        "dashboard_description": description,
        "modules": modules,
        "quick_actions": quick_actions or [],
        "platform_notifications": notifications,
        "unread_notification_count": unread_notification_count,
    }

    if extra_context:
        context.update(extra_context)

    return render(
        request,
        "dashboard/role_dashboard.html",
        context,
    )



def _mosque_admin_overview(request):
    """Build a compact operational overview for the Mosque Admin workspace."""

    memberships = list(
        MosqueMembership.objects.filter(
            user=request.user,
            is_active=True,
        )
        .select_related(
            "mosque",
            "mosque__province",
            "mosque__district",
            "mosque__divisional_secretariat",
            "mosque__gn_division",
        )
        .order_by("-mosque__updated_at")
    )

    mosques = [membership.mosque for membership in memberships]
    mosque_ids = [mosque.pk for mosque in mosques]

    mosque_counts = {
        "total": len(mosques),
        "approved": sum(
            mosque.status == MosqueStatus.APPROVED for mosque in mosques
        ),
        "pending": sum(
            mosque.status == MosqueStatus.SUBMITTED for mosque in mosques
        ),
        "draft": sum(
            mosque.status == MosqueStatus.DRAFT for mosque in mosques
        ),
        "rejected": sum(
            mosque.status == MosqueStatus.REJECTED for mosque in mosques
        ),
    }

    mosque_cards = []
    status_classes = {
        MosqueStatus.APPROVED: "success",
        MosqueStatus.SUBMITTED: "warning",
        MosqueStatus.DRAFT: "secondary",
        MosqueStatus.REJECTED: "danger",
    }

    for membership in memberships[:5]:
        mosque = membership.mosque

        profile_completion = None
        if mosque.status == MosqueStatus.APPROVED:
            try:
                profile = MosqueOperationalProfile.objects.get(mosque=mosque)
            except MosqueOperationalProfile.DoesNotExist:
                profile_completion = 0
            else:
                profile_completion = profile.profile_completion_percent

        mosque_cards.append(
            {
                "mosque": mosque,
                "membership": membership,
                "status_class": status_classes.get(
                    mosque.status,
                    "secondary",
                ),
                "profile_completion": profile_completion,
            }
        )

    support_requests = MosqueSupportRequest.objects.filter(
        mosque_id__in=mosque_ids,
    ).select_related(
        "mosque",
    )

    support_counts = {
        "total": support_requests.count(),
        "open": support_requests.exclude(
            status__in=[
                SupportRequestStatus.COMPLETED,
                SupportRequestStatus.REJECTED,
                SupportRequestStatus.CANCELLED,
            ]
        ).count(),
        "action_required": support_requests.filter(
            status=SupportRequestStatus.DOCUMENTS_REQUIRED,
        ).count(),
        "completed": support_requests.filter(
            status=SupportRequestStatus.COMPLETED,
        ).count(),
    }

    support_status_classes = {
        SupportRequestStatus.DRAFT: "secondary",
        SupportRequestStatus.SUBMITTED: "info",
        SupportRequestStatus.UNDER_REVIEW: "warning",
        SupportRequestStatus.DOCUMENTS_REQUIRED: "danger",
        SupportRequestStatus.APPROVED: "success",
        SupportRequestStatus.IN_PROGRESS: "primary",
        SupportRequestStatus.COMPLETED: "success",
        SupportRequestStatus.REJECTED: "danger",
        SupportRequestStatus.CANCELLED: "secondary",
    }

    recent_support_requests = []
    for support_request in support_requests.order_by("-updated_at")[:5]:
        recent_support_requests.append(
            {
                "request": support_request,
                "status_class": support_status_classes.get(
                    support_request.status,
                    "secondary",
                ),
            }
        )

    return {
        "mosque_admin_overview": True,
        "mosque_counts": mosque_counts,
        "mosque_cards": mosque_cards,
        "support_counts": support_counts,
        "recent_support_requests": recent_support_requests,
        "has_approved_mosque": mosque_counts["approved"] > 0,
    }


@role_required(UserRole.MOSQUE_ADMIN)
def mosque_admin_dashboard(request):
    return _render_dashboard(
        request,
        _("Mosque Admin Dashboard"),
        _("Manage mosque registrations, approved mosque profiles, support requests and account activity from one workspace."),
        [
            (_("Mosque Registration"), _("Register new mosques and follow Platform Admin approval status."), "bi-building-add"),
            (_("Mosque Portal"), _("Manage approved mosque public profile, committee, documents and portal users."), "bi-grid"),
            (_("Support Requests"), _("Create and track construction, salary, utility, maintenance and other mosque assistance requests."), "bi-hand-heart"),
        ],
        quick_actions=[
            (_("Support Requests"), "support_requests:my_requests", "bi-hand-heart"),
            (_("New Support Request"), "support_requests:create", "bi-plus-circle"),
            (_("My Mosques"), "mosques:my_mosques", "bi-buildings"),
            (_("Register Mosque"), "mosques:create", "bi-building-add"),
        ],
        extra_context=_mosque_admin_overview(request),
    )


@role_required(UserRole.MOSQUE_STAFF)
def mosque_staff_dashboard(request):
    return _render_dashboard(
        request,
        _("Mosque Staff Dashboard"),
        _("Access the mosque functions assigned to staff members."),
        [
            (_("Mosque Portal"), _("View approved mosque operational profiles where you have active staff access."), "bi-grid"),
            (_("Committee & Documents"), _("View committee contacts and mosque documents shared through the portal."), "bi-folder2-open"),
            (_("Support Requests"), _("View support requests for mosques where you have active staff access."), "bi-hand-heart"),
        ],
        quick_actions=[
            (_("Support Requests"), "support_requests:my_requests", "bi-hand-heart"),
            (_("My Mosques"), "mosques:my_mosques", "bi-buildings"),
        ],
    )


@role_required(UserRole.DISTRICT_OFFICER)
def district_officer_dashboard(request):
    assignment = DistrictOfficerAssignment.objects.filter(
        user=request.user,
        is_active=True,
    ).select_related("district", "district__province").first()

    if assignment:
        assignment_text = _("Assigned district: %(district)s (%(province)s)") % {
            "district": assignment.district.localized_name,
            "province": assignment.district.province.localized_name,
        }
    else:
        assignment_text = _("No active district has been assigned yet.")

    return _render_dashboard(
        request,
        _("District Officer Dashboard"),
        _("Access district-level operational functions for your assigned district."),
        [
            (_("District Assignment"), assignment_text, "bi-geo-alt"),
            (_("Mosque Information"), _("District-level mosque information access can be added in a later operational phase."), "bi-buildings"),
            (_("Support Reviews"), _("District-level support-request review will be connected to the support engine."), "bi-clipboard-check"),
        ],
    )


@role_required(UserRole.SUPPORT_OFFICER)
def support_officer_dashboard(request):
    return _render_dashboard(
        request,
        _("Support Officer Dashboard"),
        _("Review and process mosque support requests."),
        [
            (_("Request Queue"), _("Review submitted and resubmitted mosque support requests."), "bi-inboxes"),
            (_("Additional Information"), _("Request missing information or supporting documents and track resubmissions."), "bi-file-earmark-plus"),
            (_("Request Status"), _("Move approved assistance through In Progress and Completed states."), "bi-arrow-repeat"),
        ],
        quick_actions=[
            (_("Support Request Queue"), "support_requests:review_queue", "bi-inboxes"),
        ],
    )


@role_required(UserRole.PLATFORM_ADMIN)
def platform_admin_dashboard(request):
    return _render_dashboard(
        request,
        _("Platform Admin Dashboard"),
        _("Administer users, locations and Platform Admin mosque approvals."),
        [
            (_("User Access"), _("Create users and assign platform roles from the administration area."), "bi-people"),
            (_("Location Management"), _("Manage provinces, districts, DS divisions, GN divisions and district officer assignments."), "bi-geo-alt"),
            (_("Mosque Management"), _("Approve or reject mosque registration applications before they enter the public directory."), "bi-buildings"),
            (_("Support Requests"), _("Review and process mosque assistance requests across the platform."), "bi-hand-heart"),
        ],
        quick_actions=[
            (_("Platform Control Center"), "platform_control:overview", "bi-speedometer2"),
            (_("Support Request Queue"), "support_requests:review_queue", "bi-inboxes"),
            (_("Mosque Approval Queue"), "mosques:review_queue", "bi-building-check"),
            (_("Location Management"), "locations:management", "bi-geo-alt"),
        ],
    )


@role_required(UserRole.SUPER_ADMIN)
def super_admin_dashboard(request):
    return _render_dashboard(
        request,
        _("Super Admin Dashboard"),
        _("Full administrative access to the Sri Lanka Mosque Platform."),
        [
            (_("Django Administration"), _("Manage users, permissions and system records."), "bi-shield-lock"),
            (_("Mosque Registration"), _("Oversee Platform Admin mosque registration approvals."), "bi-buildings"),
            (_("Platform Configuration"), _("Manage the administrative location hierarchy and platform configuration."), "bi-gear"),
            (_("Support Requests"), _("Oversee mosque support requests and the full assistance workflow."), "bi-hand-heart"),
        ],
        quick_actions=[
            (_("Platform Control Center"), "platform_control:overview", "bi-speedometer2"),
            (_("Support Request Queue"), "support_requests:review_queue", "bi-inboxes"),
            (_("Mosque Approval Queue"), "mosques:review_queue", "bi-building-check"),
            (_("Location Management"), "locations:management", "bi-geo-alt"),
        ],
    )
