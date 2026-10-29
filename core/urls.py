from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("services/", views.services, name="services"),
    path("contact/", views.contact, name="contact"),

    # Prayer Times / AlAdhan integration.
    path(
        "prayer-times/",
        views.prayer_times_home,
        name="prayer_times",
    ),
    path(
        "prayer-times/api/current/",
        views.prayer_times_current_api,
        name="prayer_times_current_api",
    ),
    path(
        "prayer-times/api/divisional-secretariats/",
        views.prayer_times_ds_suggestions,
        name="prayer_times_ds_suggestions",
    ),
    path(
        "prayer-times/api/divisional-secretariats/<int:ds_id>/",
        views.prayer_times_ds_api,
        name="prayer_times_ds_api",
    ),
    path(
        "prayer-times/divisional-secretariats/",
        views.prayer_times_ds_index,
        name="prayer_times_ds_index",
    ),
    path(
        "prayer-times/divisional-secretariats/<int:ds_id>/",
        views.prayer_times_ds_detail,
        name="prayer_times_ds_detail",
    ),
]
