from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserRole


User = get_user_model()


class PasswordResetFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="mosqueadmin1",
            email="mosqueadmin@example.com",
            password="OldSecurePassword123!",
            role=UserRole.MOSQUE_ADMIN,
            is_active=True,
        )

    def test_login_page_has_forgot_password_link(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("accounts:password_reset"))

    def test_known_email_sends_reset_email(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": self.user.email},
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Password Reset", mail.outbox[0].subject)
        self.assertIn("/accounts/password/reset/", mail.outbox[0].body)

    def test_unknown_email_does_not_reveal_account_status(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": "unknown@example.com"},
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_inactive_account_does_not_receive_reset_email(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": self.user.email},
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)
