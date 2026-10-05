from django.urls import path

from . import views

app_name = "mosques"

urlpatterns = [
    path("", views.mosque_directory, name="directory"),
    path("register/", views.mosque_create, name="create"),
    path("my/", views.my_mosques, name="my_mosques"),

    path("review/", views.review_queue, name="review_queue"),
    path("review/<str:mosque_id>/", views.review_detail, name="review_detail"),
    path("review/<str:mosque_id>/action/", views.review_action, name="review_action"),

    path("<str:mosque_id>/portal/", views.mosque_portal, name="portal"),
    path("<str:mosque_id>/portal/profile/edit/", views.operational_profile_edit, name="operational_profile_edit"),
    path("<str:mosque_id>/", views.mosque_detail, name="detail"),
    path("<str:mosque_id>/public/", views.public_mosque_detail, name="public_detail"),
    path("<str:mosque_id>/edit/", views.mosque_edit, name="edit"),
    path("<str:mosque_id>/submit/", views.mosque_submit, name="submit"),

    path("<str:mosque_id>/documents/add/", views.document_add, name="document_add"),
    path(
        "<str:mosque_id>/documents/<int:document_id>/delete/",
        views.document_delete,
        name="document_delete",
    ),

    path("<str:mosque_id>/committee/add/", views.committee_add, name="committee_add"),
    path(
        "<str:mosque_id>/committee/<int:member_id>/edit/",
        views.committee_edit,
        name="committee_edit",
    ),
    path(
        "<str:mosque_id>/committee/<int:member_id>/delete/",
        views.committee_delete,
        name="committee_delete",
    ),

    path("<str:mosque_id>/members/add/", views.membership_add, name="membership_add"),
    path(
        "<str:mosque_id>/members/<int:membership_id>/remove/",
        views.membership_remove,
        name="membership_remove",
    ),
]
