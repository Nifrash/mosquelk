from django.urls import path

from . import views

app_name = "mosques"

urlpatterns = [
    # ============================================================
    # PUBLIC MOSQUE DIRECTORY
    # ============================================================
    path("", views.mosque_directory, name="directory"),

    # ============================================================
    # MOSQUE REGISTRATION
    # ============================================================
    path(
        "register/start/",
        views.registration_start,
        name="registration_start",
    ),
    path(
        "register/",
        views.mosque_create,
        name="create",
    ),

    # ============================================================
    # MOSQUE ADMIN - MY MOSQUES
    # ============================================================
    path(
        "my/",
        views.my_mosques,
        name="my_mosques",
    ),

    # ============================================================
    # PLATFORM ADMIN / REVIEW WORKFLOW
    # ============================================================
    path(
        "review/",
        views.review_queue,
        name="review_queue",
    ),
    path(
        "review/<str:mosque_id>/",
        views.review_detail,
        name="review_detail",
    ),
    path(
        "review/<str:mosque_id>/action/",
        views.review_action,
        name="review_action",
    ),

    # ============================================================
    # MOSQUE PORTAL
    # ============================================================
    path(
        "<str:mosque_id>/portal/",
        views.mosque_portal,
        name="portal",
    ),
    path(
        "<str:mosque_id>/portal/profile/edit/",
        views.operational_profile_edit,
        name="operational_profile_edit",
    ),

    # ============================================================
    # MOSQUE DETAILS
    # ============================================================
    path(
        "<str:mosque_id>/",
        views.mosque_detail,
        name="detail",
    ),
    path(
        "<str:mosque_id>/public/",
        views.public_mosque_detail,
        name="public_detail",
    ),
    path(
        "<str:mosque_id>/edit/",
        views.mosque_edit,
        name="edit",
    ),
    path(
        "<str:mosque_id>/submit/",
        views.mosque_submit,
        name="submit",
    ),

    # ============================================================
    # MOSQUE DOCUMENTS
    # ============================================================
    path(
        "<str:mosque_id>/documents/add/",
        views.document_add,
        name="document_add",
    ),
    path(
        "<str:mosque_id>/documents/<int:document_id>/delete/",
        views.document_delete,
        name="document_delete",
    ),

    # ============================================================
    # MOSQUE COMMITTEE
    # ============================================================
    path(
        "<str:mosque_id>/committee/add/",
        views.committee_add,
        name="committee_add",
    ),
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

    # ============================================================
    # MOSQUE MEMBERS / PORTAL USERS
    # ============================================================
    path(
        "<str:mosque_id>/members/add/",
        views.membership_add,
        name="membership_add",
    ),
    path(
        "<str:mosque_id>/members/<int:membership_id>/remove/",
        views.membership_remove,
        name="membership_remove",
    ),
]