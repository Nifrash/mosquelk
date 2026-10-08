from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from support_requests.notifications import notify_platform_mosque_submitted

from .access import assert_can_manage_mosque
from .models import Mosque, MosqueStatus


@transaction.atomic
def submit_mosque_registration(*, mosque_id, user):
    mosque = Mosque.objects.select_for_update().get(mosque_id=mosque_id)
    assert_can_manage_mosque(user, mosque)

    if not mosque.is_editable:
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

    transaction.on_commit(
        lambda: notify_platform_mosque_submitted(
            mosque,
            actor=user,
        )
    )
    return mosque
