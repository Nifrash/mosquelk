from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core import views as core_views


urlpatterns = [
    path("", core_views.root_home_redirect, name="root_home"),
    path(
        "language/<str:language_code>/",
        core_views.switch_language,
        name="switch_language",
    ),
    path("i18n/", include("django.conf.urls.i18n")),
]


urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("locations/", include("locations.urls")),
    path("mosques/", include("mosques.urls")),
    path("support/", include("support_requests.urls")),

    # Phase 9/10 global notification center.
    # This resolves {% url 'notifications:center' %} in the shared navbar.
    path("notifications/", include("support_requests.notification_urls")),

    path("control/", include("platform_control.urls")),
    path("", include("core.urls")),
)


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
