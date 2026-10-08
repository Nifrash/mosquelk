from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_center, name="center"),
    path("preferences/", views.notification_preferences, name="preferences"),
    path("mark-all-read/", views.notifications_mark_all_read_global, name="mark_all_read"),
    path("<int:notification_id>/open/", views.notification_open_global, name="open"),
]
