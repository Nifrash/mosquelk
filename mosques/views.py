from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.models import UserRole
from dashboard.access import role_required
from locations.models import District

from .access import (
    assert_can_manage_mosque,
    assert_can_view_private_mosque,
    can_manage_mosque,
    is_platform_reviewer,
)
from .forms import (
    MosqueCommitteeMemberForm,
    MosqueDocumentForm,
    MosqueMembershipForm,
    MosqueOperationalProfileForm,
    MosqueRegistrationForm,
    MosqueReviewForm,
)
from .models import (
    DocumentType,
    Mosque,
    MosqueCommitteeMember,
    MosqueDocument,
    MosqueMembership,
    MosqueMembershipRole,
    MosqueOperationalProfile,
    MosqueReviewHistory,
    MosqueStatus,
)


def _mosque_queryset():
    return Mosque.objects.select_related(
        "province",
        "district",
        "divisional_secretariat",
        "gn_division",
        "created_by",
        "reviewed_by",
        "operational_profile",
    ).prefetch_related(
        "documents",
        "committee_members",
        "memberships__user",
        "review_history__reviewer",
    )



def _attach_public_photo(mosque):
    photo = next(
        (
            document
            for document in mosque.documents.all()
            if document.document_type == DocumentType.PHOTO and document.file
        ),
        None,
    )
    mosque.public_photo_url = photo.file.url if photo else ""
    return mosque


def _get_mosque(mosque_id):
    return get_object_or_404(_mosque_queryset(), mosque_id=mosque_id)


def _assert_editable(mosque):
    if not mosque.is_editable:
        raise PermissionDenied


def _assert_content_editable(mosque):
    if mosque.status not in {MosqueStatus.DRAFT, MosqueStatus.APPROVED}:
        raise PermissionDenied


def _get_operational_profile(mosque):
    profile, _ = MosqueOperationalProfile.objects.get_or_create(mosque=mosque)
    return profile


def _reviewer_queryset_for_user(user):
    queryset = _mosque_queryset().exclude(status=MosqueStatus.DRAFT)

    if is_platform_reviewer(user):
        return queryset

    return queryset.none()


def mosque_directory(request):
    queryset = _mosque_queryset().filter(status=MosqueStatus.APPROVED)

    query = request.GET.get("q", "").strip()
    district_id = request.GET.get("district", "").strip()

    if query:
        queryset = queryset.filter(
            Q(mosque_id__icontains=query)
            | Q(name_en__icontains=query)
            | Q(name_ta__icontains=query)
            | Q(name_ar__icontains=query)
            | Q(city_or_town__icontains=query)
            | Q(district__name_en__icontains=query)
        )

    if district_id:
        queryset = queryset.filter(district_id=district_id)

    mosques = list(queryset.order_by("name_en"))
    for mosque in mosques:
        _attach_public_photo(mosque)

    return render(
        request,
        "mosques/directory.html",
        {
            "mosques": mosques,
            "query": query,
            "selected_district": district_id,
            "districts": District.objects.filter(is_active=True).order_by("name_en"),
            "result_count": len(mosques),
        },
    )


def public_mosque_detail(request, mosque_id):
    mosque = get_object_or_404(
        _mosque_queryset(),
        mosque_id=mosque_id,
        status=MosqueStatus.APPROVED,
    )
    profile = MosqueOperationalProfile.objects.filter(mosque=mosque).first()
    _attach_public_photo(mosque)
    return render(
        request,
        "mosques/public_detail.html",
        {"mosque": mosque, "profile": profile},
    )


@login_required
def my_mosques(request):
    memberships = MosqueMembership.objects.filter(
        user=request.user,
        is_active=True,
    ).select_related(
        "mosque",
        "mosque__district",
    ).order_by("mosque__name_en")

    return render(
        request,
        "mosques/my_mosques.html",
        {"memberships": memberships},
    )


@role_required(UserRole.MOSQUE_ADMIN)
def mosque_create(request):
    form = MosqueRegistrationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            mosque = form.save(commit=False)
            mosque.created_by = request.user
            mosque.status = MosqueStatus.DRAFT
            mosque.save()

            MosqueMembership.objects.get_or_create(
                mosque=mosque,
                user=request.user,
                defaults={
                    "membership_role": MosqueMembershipRole.ADMIN,
                    "is_active": True,
                    "added_by": request.user,
                },
            )

        messages.success(
            request,
            _("Mosque registration draft created successfully. Add committee members or documents, then submit it for Platform Admin approval."),
        )
        return redirect("mosques:detail", mosque_id=mosque.mosque_id)

    return render(
        request,
        "mosques/registration_form.html",
        {
            "form": form,
            "is_edit": False,
        },
    )


@login_required
def mosque_detail(request, mosque_id):
    mosque = _get_mosque(mosque_id)
    assert_can_view_private_mosque(request.user, mosque)

    membership = MosqueMembership.objects.filter(
        user=request.user,
        mosque=mosque,
        is_active=True,
    ).first()

    can_manage = can_manage_mosque(request.user, mosque)
    profile = MosqueOperationalProfile.objects.filter(mosque=mosque).first()

    return render(
        request,
        "mosques/detail.html",
        {
            "mosque": mosque,
            "membership": membership,
            "can_manage": can_manage,
            "can_manage_content": can_manage and mosque.status in {MosqueStatus.DRAFT, MosqueStatus.APPROVED},
            "profile": profile,
        },
    )


@login_required
def mosque_edit(request, mosque_id):
    mosque = _get_mosque(mosque_id)
    assert_can_manage_mosque(request.user, mosque)
    _assert_editable(mosque)

    form = MosqueRegistrationForm(request.POST or None, instance=mosque)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Mosque registration details updated."))
        return redirect("mosques:detail", mosque_id=mosque.mosque_id)

    return render(
        request,
        "mosques/registration_form.html",
        {
            "form": form,
            "mosque": mosque,
            "is_edit": True,
        },
    )


@login_required
@transaction.atomic
def mosque_submit(request, mosque_id):
    mosque = _get_mosque(mosque_id)
    assert_can_manage_mosque(request.user, mosque)
    _assert_editable(mosque)

    if request.method != "POST":
        raise PermissionDenied

    mosque.status = MosqueStatus.SUBMITTED
    mosque.submitted_at = timezone.now()
    mosque.reviewed_at = None
    mosque.reviewed_by = None
    mosque.review_notes = ""
    mosque.save(
        update_fields=[
            "status",
            "submitted_at",
            "reviewed_at",
            "reviewed_by",
            "review_notes",
            "updated_at",
        ]
    )


    messages.success(
        request,
        _("Mosque registration submitted successfully for Platform Admin approval."),
    )
    return redirect("mosques:detail", mosque_id=mosque.mosque_id)


@login_required
def document_add(request, mosque_id):
    mosque = _get_mosque(mosque_id)
    assert_can_manage_mosque(request.user, mosque)
    _assert_content_editable(mosque)

    form = MosqueDocumentForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        document = form.save(commit=False)
        document.mosque = mosque
        document.uploaded_by = request.user
        document.save()
        messages.success(request, _("Supporting document uploaded."))
        target = "mosques:portal" if mosque.status == MosqueStatus.APPROVED else "mosques:detail"
        return redirect(target, mosque_id=mosque.mosque_id)

    return render(
        request,
        "mosques/document_form.html",
        {"mosque": mosque, "form": form},
    )


@login_required
def document_delete(request, mosque_id, document_id):
    mosque = _get_mosque(mosque_id)
    assert_can_manage_mosque(request.user, mosque)
    _assert_content_editable(mosque)

    document = get_object_or_404(MosqueDocument, pk=document_id, mosque=mosque)

    if request.method != "POST":
        raise PermissionDenied

    if document.file:
        document.file.delete(save=False)
    document.delete()
    messages.success(request, _("Document removed."))
    target = "mosques:portal" if mosque.status == MosqueStatus.APPROVED else "mosques:detail"
    return redirect(target, mosque_id=mosque.mosque_id)


@login_required
def committee_add(request, mosque_id):
    mosque = _get_mosque(mosque_id)
    assert_can_manage_mosque(request.user, mosque)
    _assert_content_editable(mosque)

    form = MosqueCommitteeMemberForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        member = form.save(commit=False)
        member.mosque = mosque
        member.save()
        messages.success(request, _("Committee member added."))
        target = "mosques:portal" if mosque.status == MosqueStatus.APPROVED else "mosques:detail"
        return redirect(target, mosque_id=mosque.mosque_id)

    return render(
        request,
        "mosques/committee_form.html",
        {"mosque": mosque, "form": form},
    )


@login_required
def committee_delete(request, mosque_id, member_id):
    mosque = _get_mosque(mosque_id)
    assert_can_manage_mosque(request.user, mosque)
    _assert_content_editable(mosque)

    member = get_object_or_404(MosqueCommitteeMember, pk=member_id, mosque=mosque)

    if request.method != "POST":
        raise PermissionDenied

    member.delete()
    messages.success(request, _("Committee member removed."))
    target = "mosques:portal" if mosque.status == MosqueStatus.APPROVED else "mosques:detail"
    return redirect(target, mosque_id=mosque.mosque_id)


@login_required
def membership_add(request, mosque_id):
    mosque = _get_mosque(mosque_id)
    assert_can_manage_mosque(request.user, mosque)

    form = MosqueMembershipForm(request.POST or None, mosque=mosque)

    if request.method == "POST" and form.is_valid():
        membership = form.save(commit=False)
        membership.mosque = mosque
        membership.added_by = request.user
        membership.save()
        messages.success(request, _("Mosque user access added."))
        target = "mosques:portal" if mosque.status == MosqueStatus.APPROVED else "mosques:detail"
        return redirect(target, mosque_id=mosque.mosque_id)

    return render(
        request,
        "mosques/membership_form.html",
        {"mosque": mosque, "form": form},
    )


@login_required
def membership_remove(request, mosque_id, membership_id):
    mosque = _get_mosque(mosque_id)
    assert_can_manage_mosque(request.user, mosque)

    membership = get_object_or_404(
        MosqueMembership,
        pk=membership_id,
        mosque=mosque,
    )

    if request.method != "POST":
        raise PermissionDenied

    if membership.user_id == mosque.created_by_id:
        messages.error(
            request,
            _("The original mosque administrator cannot be removed from this registration."),
        )
    else:
        membership.delete()
        messages.success(request, _("Mosque user access removed."))

    target = "mosques:portal" if mosque.status == MosqueStatus.APPROVED else "mosques:detail"
    return redirect(target, mosque_id=mosque.mosque_id)


@login_required
def mosque_portal(request, mosque_id):
    mosque = _get_mosque(mosque_id)
    assert_can_view_private_mosque(request.user, mosque)

    if mosque.status != MosqueStatus.APPROVED:
        messages.info(
            request,
            _("The operational mosque portal becomes available after Platform Admin approval."),
        )
        return redirect("mosques:detail", mosque_id=mosque.mosque_id)

    membership = MosqueMembership.objects.filter(
        user=request.user,
        mosque=mosque,
        is_active=True,
    ).first()
    profile = _get_operational_profile(mosque)
    active_memberships = mosque.memberships.filter(is_active=True).count()

    return render(
        request,
        "mosques/portal_dashboard.html",
        {
            "mosque": mosque,
            "profile": profile,
            "membership": membership,
            "can_manage": can_manage_mosque(request.user, mosque),
            "committee_count": mosque.committee_members.count(),
            "document_count": mosque.documents.count(),
            "user_count": active_memberships,
        },
    )


@login_required
def operational_profile_edit(request, mosque_id):
    mosque = _get_mosque(mosque_id)
    assert_can_manage_mosque(request.user, mosque)

    if mosque.status != MosqueStatus.APPROVED:
        raise PermissionDenied

    profile = _get_operational_profile(mosque)
    form = MosqueOperationalProfileForm(request.POST or None, instance=profile)

    if request.method == "POST" and form.is_valid():
        profile = form.save(commit=False)
        profile.updated_by = request.user
        profile.save()
        messages.success(request, _("Mosque public and operational profile updated."))
        return redirect("mosques:portal", mosque_id=mosque.mosque_id)

    return render(
        request,
        "mosques/operational_profile_form.html",
        {"mosque": mosque, "form": form},
    )


@login_required
def committee_edit(request, mosque_id, member_id):
    mosque = _get_mosque(mosque_id)
    assert_can_manage_mosque(request.user, mosque)
    _assert_content_editable(mosque)

    member = get_object_or_404(
        MosqueCommitteeMember,
        pk=member_id,
        mosque=mosque,
    )
    form = MosqueCommitteeMemberForm(request.POST or None, instance=member)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Committee member updated."))
        target = "mosques:portal" if mosque.status == MosqueStatus.APPROVED else "mosques:detail"
        return redirect(target, mosque_id=mosque.mosque_id)

    return render(
        request,
        "mosques/committee_form.html",
        {"mosque": mosque, "form": form, "is_edit": True},
    )


@role_required(
    UserRole.PLATFORM_ADMIN,
    UserRole.SUPER_ADMIN,
)
def review_queue(request):
    queryset = _reviewer_queryset_for_user(request.user)

    status = request.GET.get("status", "").strip()
    query = request.GET.get("q", "").strip()

    if status in MosqueStatus.values:
        queryset = queryset.filter(status=status)

    if query:
        queryset = queryset.filter(
            Q(mosque_id__icontains=query)
            | Q(name_en__icontains=query)
            | Q(name_ta__icontains=query)
            | Q(name_ar__icontains=query)
            | Q(district__name_en__icontains=query)
        )

    return render(
        request,
        "mosques/review_queue.html",
        {
            "mosques": queryset.order_by("-submitted_at", "name_en"),
            "status_choices": MosqueStatus.choices,
            "selected_status": status,
            "query": query,
        },
    )


@role_required(
    UserRole.PLATFORM_ADMIN,
    UserRole.SUPER_ADMIN,
)
def review_detail(request, mosque_id):
    mosque = get_object_or_404(
        _reviewer_queryset_for_user(request.user),
        mosque_id=mosque_id,
    )

    return render(
        request,
        "mosques/review_detail.html",
        {
            "mosque": mosque,
            "review_form": MosqueReviewForm(),
        },
    )


@role_required(
    UserRole.PLATFORM_ADMIN,
    UserRole.SUPER_ADMIN,
)
@transaction.atomic
def review_action(request, mosque_id):
    if request.method != "POST":
        raise PermissionDenied

    mosque = get_object_or_404(
        _reviewer_queryset_for_user(request.user),
        mosque_id=mosque_id,
    )

    if mosque.status in {MosqueStatus.APPROVED, MosqueStatus.REJECTED}:
        messages.error(request, _("This registration has already reached a final status."))
        return redirect("mosques:review_detail", mosque_id=mosque.mosque_id)

    form = MosqueReviewForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "mosques/review_detail.html",
            {"mosque": mosque, "review_form": form},
            status=400,
        )

    target = form.cleaned_data["action"]
    notes = form.cleaned_data["notes"].strip()

    allowed_targets = {
        MosqueStatus.APPROVED,
        MosqueStatus.REJECTED,
    }
    if target not in allowed_targets:
        raise PermissionDenied

    previous_status = mosque.status
    mosque.status = target
    mosque.reviewed_by = request.user
    mosque.reviewed_at = timezone.now()
    mosque.review_notes = notes
    mosque.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "updated_at",
        ]
    )

    MosqueReviewHistory.objects.create(
        mosque=mosque,
        from_status=previous_status,
        to_status=target,
        reviewer=request.user,
        notes=notes,
    )

    messages.success(
        request,
        _("Registration status updated to %(status)s.")
        % {"status": mosque.get_status_display()},
    )
    return redirect("mosques:review_detail", mosque_id=mosque.mosque_id)
