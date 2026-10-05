from django.test import TestCase
from django.urls import reverse


class MultilingualUiTests(TestCase):
    def test_tamil_home_uses_tamil_translation(self):
        response = self.client.get("/ta/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "முகப்பு")
        self.assertContains(response, 'lang="ta"')
        self.assertContains(response, 'dir="ltr"')

    def test_arabic_home_uses_arabic_translation_and_rtl(self):
        response = self.client.get("/ar/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "الرئيسية")
        self.assertContains(response, 'lang="ar"')
        self.assertContains(response, 'dir="rtl"')

    def test_english_home_remains_ltr(self):
        response = self.client.get("/en/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lang="en"')
        self.assertContains(response, 'dir="ltr"')

    def test_arabic_support_label_translation(self):
        response = self.client.get("/ar/")
        self.assertContains(response, "طلب الدعم")

    def test_tamil_mosque_directory_label_translation(self):
        response = self.client.get("/ta/")
        self.assertContains(response, "பள்ளிவாசல் அடைவு")
