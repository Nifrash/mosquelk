from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
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
