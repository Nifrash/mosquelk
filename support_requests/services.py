from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from .access import assert_can_manage_support_request
from .models import MosqueSupportRequest, SupportRequestHistory, SupportRequestStatus
from .notifications import notify_review_team_submission


@transaction.atomic
def submit_support_request(*, request_no, user):
    support_request = (
        MosqueSupportRequest.objects.select_for_update()
        .select_related("mosque", "created_by")
        .get(request_no=request_no)
    )
    assert_can_manage_support_request(user, support_request)

    if support_request.status not in {
        SupportRequestStatus.DRAFT,
        SupportRequestStatus.DOCUMENTS_REQUIRED,
    }:
        raise PermissionDenied

    old_status = support_request.status
    is_resubmission = old_status == SupportRequestStatus.DOCUMENTS_REQUIRED

    support_request.status = SupportRequestStatus.SUBMITTED
    support_request.submitted_at = timezone.now()
    support_request.latest_admin_note = ""
    support_request.save(
        update_fields=[
            "status",
            "submitted_at",
            "latest_admin_note",
            "updated_at",
        ]
    )

    SupportRequestHistory.objects.create(
        support_request=support_request,
        from_status=old_status,
        to_status=SupportRequestStatus.SUBMITTED,
        actor=user,
        notes=_(
            "Resubmitted by mosque administration after adding requested information/documents."
            if is_resubmission
            else "Submitted by mosque administration."
        ),
    )

    transaction.on_commit(
        lambda: notify_review_team_submission(
            support_request,
            resubmitted=is_resubmission,
            actor=user,
        )
    )
    return support_request, is_resubmission
