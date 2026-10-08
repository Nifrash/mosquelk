from .models import SupportNotification


def platform_notifications(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {
            "GLOBAL_UNREAD_NOTIFICATION_COUNT": 0,
            "GLOBAL_RECENT_NOTIFICATIONS": [],
        }

    queryset = SupportNotification.objects.filter(
        user=request.user,
        dashboard_visible=True,
    )

    return {
        "GLOBAL_UNREAD_NOTIFICATION_COUNT": queryset.filter(is_read=False).count(),
        "GLOBAL_RECENT_NOTIFICATIONS": queryset[:5],
    }
