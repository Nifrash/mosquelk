from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path(
        "password/reset/",
        views.PlatformPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password/reset/done/",
        views.PlatformPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        views.PlatformPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/complete/",
        views.PlatformPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path(
        "register/mosque-admin/",
        views.mosque_admin_register,
        name="mosque_admin_register",
    ),
    path("otp/verify/", views.otp_verify, name="otp_verify"),
    path("otp/resend/", views.otp_resend, name="otp_resend"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
]
