from django.urls import path

from . import views

app_name = "platform_control"

urlpatterns = [
    path("", views.overview, name="overview"),

    path("users/", views.user_list, name="user_list"),
    path("users/add/", views.user_create, name="user_create"),
    path(
        "users/<int:user_id>/",
        views.user_detail,
        name="user_detail",
    ),
    path(
        "users/<int:user_id>/edit/",
        views.user_edit,
        name="user_edit",
    ),

    path(
        "notification-deliveries/",
        views.notification_delivery_monitor,
        name="notification_delivery_monitor",
    ),
]
