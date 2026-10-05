from django.urls import path

from . import views

app_name = "support_requests"

urlpatterns = [
    path("", views.my_requests, name="my_requests"),
    path("new/", views.support_request_create, name="create"),

    path("notifications/", views.notification_center, name="notifications"),
    path(
        "notifications/mark-all-read/",
        views.notifications_mark_all_read,
        name="notifications_mark_all_read",
    ),
    path(
        "notifications/<int:notification_id>/open/",
        views.notification_open,
        name="notification_open",
    ),

    path("review/", views.review_queue, name="review_queue"),
    path(
        "review/<str:request_no>/",
        views.review_detail,
        name="review_detail",
    ),
    path(
        "review/<str:request_no>/action/",
        views.review_action,
        name="review_action",
    ),

    path(
        "<str:request_no>/",
        views.support_request_detail,
        name="detail",
    ),
    path(
        "<str:request_no>/edit/",
        views.support_request_edit,
        name="edit",
    ),
    path(
        "<str:request_no>/submit/",
        views.support_request_submit,
        name="submit",
    ),
    path(
        "<str:request_no>/cancel/",
        views.support_request_cancel,
        name="cancel",
    ),

    path(
        "<str:request_no>/documents/add/",
        views.document_add,
        name="document_add",
    ),
    path(
        "<str:request_no>/documents/<int:document_id>/delete/",
        views.document_delete,
        name="document_delete",
    ),
]
