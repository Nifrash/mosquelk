from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserRole


class MosqueRegistrationOnboardingTests(TestCase):
    def test_anonymous_user_sees_registration_start_page(self):
        response = self.client.get(reverse("mosques:registration_start"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Mosque Admin Account")

    def test_protected_mosque_form_still_requires_authentication(self):
        response = self.client.get(reverse("mosques:create"))
        self.assertEqual(response.status_code, 302)

    def test_logged_in_mosque_admin_start_redirects_to_form(self):
        user = get_user_model().objects.create_user(
            username="mosqueadmin",
            email="mosqueadmin@example.com",
            phone_number="+94770000004",
            password="StrongPass123!",
            role=UserRole.MOSQUE_ADMIN,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("mosques:registration_start"))
        self.assertRedirects(
            response,
            reverse("mosques:create"),
            fetch_redirect_response=False,
        )
