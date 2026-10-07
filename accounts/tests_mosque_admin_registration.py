from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserRole


class MosqueAdminPublicRegistrationTests(TestCase):
    def test_public_mosque_admin_registration_creates_correct_role_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:mosque_admin_register"),
            {
                "username": "newmosqueadmin",
                "first_name": "New",
                "last_name": "Admin",
                "email": "newadmin@example.com",
                "phone_number": "+94770000001",
                "preferred_language": "en",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertRedirects(
            response,
            reverse("mosques:create"),
            fetch_redirect_response=False,
        )

        user = get_user_model().objects.get(username="newmosqueadmin")
        self.assertEqual(user.role, UserRole.MOSQUE_ADMIN)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_email_is_rejected(self):
        get_user_model().objects.create_user(
            username="existing",
            email="same@example.com",
            phone_number="+94770000002",
            password="StrongPass123!",
            role=UserRole.MOSQUE_ADMIN,
        )

        response = self.client.post(
            reverse("accounts:mosque_admin_register"),
            {
                "username": "different",
                "first_name": "Another",
                "last_name": "Admin",
                "email": "SAME@example.com",
                "phone_number": "+94770000003",
                "preferred_language": "en",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertFalse(
            get_user_model().objects.filter(username="different").exists()
        )
