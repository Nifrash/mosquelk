from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("mosque-admin/", views.mosque_admin_dashboard, name="mosque_admin"),
    path("mosque-staff/", views.mosque_staff_dashboard, name="mosque_staff"),
    path("district-officer/", views.district_officer_dashboard, name="district_officer"),
    path("support-officer/", views.support_officer_dashboard, name="support_officer"),
    path("platform-admin/", views.platform_admin_dashboard, name="platform_admin"),
    path("super-admin/", views.super_admin_dashboard, name="super_admin"),
]
