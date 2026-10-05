from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import UserRole


class UniversalAuthenticationTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="mosqueadmin",
            email="admin@example.com",
            password="StrongPass123!",
            role=UserRole.MOSQUE_ADMIN,
        )

    def test_login_with_username(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "identifier": "mosqueadmin",
                "password": "StrongPass123!",
            },
        )

        self.assertRedirects(
            response,
            reverse("dashboard:home"),
            fetch_redirect_response=False,
        )

        self.assertIn("_auth_user_id", self.client.session)

    def test_login_with_email(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "identifier": "ADMIN@EXAMPLE.COM",
                "password": "StrongPass123!",
            },
        )

        self.assertRedirects(
            response,
            reverse("dashboard:home"),
            fetch_redirect_response=False,
        )

        self.assertIn("_auth_user_id", self.client.session)

    def test_mosque_admin_redirect(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:home"))

        self.assertRedirects(
            response,
            reverse("dashboard:mosque_admin"),
        )

    def test_mosque_admin_dashboard_loads(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:mosque_admin"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mosque Admin Dashboard")

    def test_wrong_role_is_forbidden(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:platform_admin"))

        self.assertEqual(response.status_code, 403)

    def test_invalid_password_does_not_login(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "identifier": "mosqueadmin",
                "password": "WrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(
            response,
            "Invalid username/email or password.",
        )
