from django.core.exceptions import PermissionDenied

from accounts.models import UserRole
from mosques.models import MosqueMembership, MosqueMembershipRole


def is_support_reviewer(user):
    return bool(
        user.is_authenticated
        and (
            user.is_superuser
            or user.role
            in {
                UserRole.SUPPORT_OFFICER,
                UserRole.PLATFORM_ADMIN,
                UserRole.SUPER_ADMIN,
            }
        )
    )


def can_view_support_request(user, support_request):
    if not user.is_authenticated:
        return False

    if is_support_reviewer(user):
        return True

    return MosqueMembership.objects.filter(
        user=user,
        mosque=support_request.mosque,
        is_active=True,
    ).exists()


def can_manage_support_request(user, support_request):
    if not user.is_authenticated:
        return False

    return MosqueMembership.objects.filter(
        user=user,
        mosque=support_request.mosque,
        membership_role=MosqueMembershipRole.ADMIN,
        is_active=True,
    ).exists()


def assert_can_view_support_request(user, support_request):
    if not can_view_support_request(user, support_request):
        raise PermissionDenied


def assert_can_manage_support_request(user, support_request):
    if not can_manage_support_request(user, support_request):
        raise PermissionDenied
