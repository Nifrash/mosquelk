import time

from django.core import mail, signing
from django.test import TestCase, override_settings
from django.urls import reverse

from core.views import (
    CONTACT_FORM_RECIPIENT,
    CONTACT_FORM_SALT,
)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Mosques Sri Lanka <noreply@mosques.lk>",
)
class SecureContactFormTests(TestCase):
    def _valid_token(self):
        return signing.dumps(
            {"created_at": time.time() - 5},
            salt=CONTACT_FORM_SALT,
            compress=True,
        )

    def _valid_payload(self):
        return {
            "name": "Test User",
            "email": "visitor@example.com",
            "subject": "Mosque registration question",
            "message": (
                "I would like some guidance about registering "
                "our mosque on the platform."
            ),
            "website": "",
            "form_token": self._valid_token(),
        }

    def test_contact_page_loads_form(self):
        response = self.client.get(
            reverse("core:contact")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'name="form_token"',
        )

    def test_valid_message_is_sent_to_info_mailbox(self):
        response = self.client.post(
            reverse("core:contact"),
            self._valid_payload(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]

        self.assertEqual(
            message.to,
            [CONTACT_FORM_RECIPIENT],
        )
        self.assertEqual(
            CONTACT_FORM_RECIPIENT,
            "info@mosques.lk",
        )
        self.assertEqual(
            message.reply_to,
            ["visitor@example.com"],
        )
        self.assertIn(
            "Mosque registration question",
            message.subject,
        )

    def test_honeypot_blocks_submission(self):
        payload = self._valid_payload()
        payload["website"] = "https://spam.example"

        response = self.client.post(
            reverse("core:contact"),
            payload,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_token_blocks_submission(self):
        payload = self._valid_payload()
        payload["form_token"] = "invalid-token"

        response = self.client.post(
            reverse("core:contact"),
            payload,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_too_fast_submission_is_blocked(self):
        payload = self._valid_payload()
        payload["form_token"] = signing.dumps(
            {"created_at": time.time()},
            salt=CONTACT_FORM_SALT,
            compress=True,
        )

        response = self.client.post(
            reverse("core:contact"),
            payload,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_subject_header_injection_is_blocked(self):
        payload = self._valid_payload()
        payload["subject"] = (
            "Question\nBcc: attacker@example.com"
        )

        response = self.client.post(
            reverse("core:contact"),
            payload,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)
