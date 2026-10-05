from django.test import TestCase
from django.urls import reverse


class PublicHomeRedesignTests(TestCase):
    def test_home_loads(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "home-hero")

    def test_home_contains_real_public_links(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, reverse("core:about"))
        self.assertContains(response, reverse("core:services"))
        self.assertContains(response, reverse("core:contact"))
        self.assertContains(response, reverse("mosques:directory"))
        self.assertContains(response, reverse("mosques:create"))
        self.assertContains(response, reverse("support_requests:create"))
        self.assertContains(response, reverse("accounts:login"))

    def test_tamil_home_has_ltr_language_markup(self):
        response = self.client.get("/ta/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lang="ta"')
        self.assertContains(response, 'dir="ltr"')

    def test_arabic_home_has_rtl_language_markup(self):
        response = self.client.get("/ar/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lang="ar"')
        self.assertContains(response, 'dir="rtl"')
