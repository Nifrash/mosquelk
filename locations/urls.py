from django.urls import path

from . import views

app_name = "locations"

urlpatterns = [
    path("management/", views.location_management, name="management"),

    path(
        "management/officer-assignments/",
        views.officer_assignment_list,
        name="officer_assignments",
    ),
    path(
        "management/officer-assignments/add/",
        views.officer_assignment_form,
        name="officer_assignment_add",
    ),
    path(
        "management/officer-assignments/<int:pk>/edit/",
        views.officer_assignment_form,
        name="officer_assignment_edit",
    ),
    path(
        "management/officer-assignments/<int:pk>/delete/",
        views.officer_assignment_delete,
        name="officer_assignment_delete",
    ),

    path("management/<str:entity>/", views.location_list, name="list"),
    path("management/<str:entity>/add/", views.location_form, name="add"),
    path(
        "management/<str:entity>/<int:pk>/edit/",
        views.location_form,
        name="edit",
    ),
    path(
        "management/<str:entity>/<int:pk>/delete/",
        views.location_delete,
        name="delete",
    ),

    path("api/districts/", views.api_districts, name="api_districts"),
    path(
        "api/ds-divisions/",
        views.api_ds_divisions,
        name="api_ds_divisions",
    ),
    path(
        "api/gn-divisions/",
        views.api_gn_divisions,
        name="api_gn_divisions",
    ),
]
