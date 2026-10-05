from django.core.exceptions import PermissionDenied

from accounts.models import UserRole
from .models import MosqueMembership, MosqueMembershipRole


def is_platform_reviewer(user):
    return user.is_superuser or user.role in {
        UserRole.PLATFORM_ADMIN,
        UserRole.SUPER_ADMIN,
    }


def get_active_membership(user, mosque):
    if not user.is_authenticated:
        return None
    return MosqueMembership.objects.filter(
        user=user,
        mosque=mosque,
        is_active=True,
    ).first()


def can_view_private_mosque(user, mosque):
    if not user.is_authenticated:
        return False

    if is_platform_reviewer(user):
        return True

    return MosqueMembership.objects.filter(
        user=user,
        mosque=mosque,
        is_active=True,
    ).exists()


def can_manage_mosque(user, mosque):
    if not user.is_authenticated:
        return False

    if is_platform_reviewer(user):
        return True

    return MosqueMembership.objects.filter(
        user=user,
        mosque=mosque,
        membership_role=MosqueMembershipRole.ADMIN,
        is_active=True,
    ).exists()


def assert_can_view_private_mosque(user, mosque):
    if not can_view_private_mosque(user, mosque):
        raise PermissionDenied


def assert_can_manage_mosque(user, mosque):
    if not can_manage_mosque(user, mosque):
        raise PermissionDenied
