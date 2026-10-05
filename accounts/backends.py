from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class UsernameOrEmailBackend(ModelBackend):
    """Authenticate an active user with either username or email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = (kwargs.get("identifier") or username or "").strip()
        if not identifier or password is None:
            return None

        UserModel = get_user_model()
        user = (
            UserModel._default_manager
            .filter(Q(username__iexact=identifier) | Q(email__iexact=identifier))
            .order_by("pk")
            .first()
        )

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
