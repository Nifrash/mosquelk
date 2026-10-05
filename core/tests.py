from django.conf import settings
from django.test import TestCase
from django.urls import reverse


class LanguageSwitchTests(TestCase):
    def test_bare_root_opens_default_language_home(self):
        response = self.client.get("/")

        self.assertRedirects(
            response,
            "/en/",
            fetch_redirect_response=False,
        )

    def test_switch_home_from_english_to_tamil(self):
        response = self.client.get(
            reverse(
                "switch_language",
                kwargs={"language_code": "ta"},
            ),
            {"next": "/en/"},
        )

        self.assertRedirects(
            response,
            "/ta/",
            fetch_redirect_response=False,
        )

        self.assertEqual(
            response.cookies[settings.LANGUAGE_COOKIE_NAME].value,
            "ta",
        )

    def test_switch_about_from_english_to_arabic(self):
        response = self.client.get(
            reverse(
                "switch_language",
                kwargs={"language_code": "ar"},
            ),
            {"next": "/en/about/"},
        )

        self.assertRedirects(
            response,
            "/ar/about/",
            fetch_redirect_response=False,
        )

    def test_switch_preserves_query_string(self):
        response = self.client.get(
            reverse(
                "switch_language",
                kwargs={"language_code": "ta"},
            ),
            {
                "next": (
                    "/en/support/"
                    "?status=SUBMITTED&q=roof"
                )
            },
        )

        self.assertRedirects(
            response,
            "/ta/support/?status=SUBMITTED&q=roof",
            fetch_redirect_response=False,
        )

    def test_switch_between_non_english_languages(self):
        response = self.client.get(
            reverse(
                "switch_language",
                kwargs={"language_code": "en"},
            ),
            {"next": "/ar/mosques/"},
        )

        self.assertRedirects(
            response,
            "/en/mosques/",
            fetch_redirect_response=False,
        )

    def test_invalid_language_returns_404(self):
        response = self.client.get(
            reverse(
                "switch_language",
                kwargs={"language_code": "xx"},
            ),
            {"next": "/en/"},
        )

        self.assertEqual(response.status_code, 404)

    def test_external_next_url_is_not_used(self):
        response = self.client.get(
            reverse(
                "switch_language",
                kwargs={"language_code": "ta"},
            ),
            {"next": "https://example.com/phishing"},
        )

        self.assertRedirects(
            response,
            "/ta/",
            fetch_redirect_response=False,
        )


from django.core import mail
from django.test import override_settings


class PublicPagesTests(TestCase):
    def test_about_services_contact_pages_load(self):
        for url in ("/en/about/", "/en/services/", "/en/contact/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_public_navigation_destinations_resolve(self):
        self.assertEqual(self.client.get("/en/").status_code, 200)
        self.assertEqual(self.client.get("/en/mosques/").status_code, 200)
        self.assertEqual(self.client.get("/en/accounts/login/").status_code, 200)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_contact_form_sends_email(self):
        response = self.client.post(
            "/en/contact/",
            {
                "name": "Test User",
                "email": "test@example.com",
                "subject": "Platform question",
                "message": "Please contact me about mosque registration.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Platform question", mail.outbox[0].subject)

    def test_tamil_public_pages_keep_ltr(self):
        response = self.client.get("/ta/about/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'dir="ltr"')

    def test_arabic_public_pages_use_rtl(self):
        response = self.client.get("/ar/services/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'dir="rtl"')
