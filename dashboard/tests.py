from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserRole


class RoleDashboardTests(TestCase):
    def test_each_role_redirects_to_its_dashboard(self):
        User = get_user_model()
        mapping = [
            (UserRole.MOSQUE_ADMIN, "dashboard:mosque_admin"),
            (UserRole.MOSQUE_STAFF, "dashboard:mosque_staff"),
            (UserRole.DISTRICT_OFFICER, "dashboard:district_officer"),
            (UserRole.SUPPORT_OFFICER, "dashboard:support_officer"),
            (UserRole.PLATFORM_ADMIN, "dashboard:platform_admin"),
        ]
        for index, (role, destination) in enumerate(mapping):
            user = User.objects.create_user(
                username=f"user{index}",
                email=f"user{index}@example.com",
                password="StrongPass123!",
                role=role,
            )
            self.client.force_login(user)
            response = self.client.get(reverse("dashboard:home"))
            self.assertRedirects(response, reverse(destination))
            self.client.logout()
