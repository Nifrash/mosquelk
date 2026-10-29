from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from locations.models import (
    District,
    DivisionalSecretariat,
    Province,
)


MOCK_PRAYER_DATA = {
    "location_label": "Akkaraipattu, Ampara",
    "precision": "divisional_secretariat",
    "timings": {
        "Fajr": "04:58",
        "Sunrise": "06:02",
        "Dhuhr": "11:55",
        "Asr": "15:16",
        "Maghrib": "17:49",
        "Isha": "18:55",
    },
    "date": {
        "readable": "29 Oct 2026",
        "gregorian": "29-10-2026",
        "hijri": "17-05-1448",
        "hijri_day": "17",
        "hijri_month": "Jumada al-awwal",
        "hijri_year": "1448",
    },
    "meta": {
        "timezone": "Asia/Colombo",
        "method": "Automatic",
    },
}


class PrayerTimesPageTests(TestCase):
    def setUp(self):
        self.province = Province.objects.create(
            code="EP",
            name_en="Eastern Province",
            is_active=True,
        )
        self.district = District.objects.create(
            province=self.province,
            code="AMP",
            name_en="Ampara",
            is_active=True,
        )
        self.ds = DivisionalSecretariat.objects.create(
            district=self.district,
            code="DCS-DS-EP-AMP-AKP",
            name_en="Akkaraipattu",
            is_active=True,
        )

    def test_prayer_times_home_loads(self):
        response = self.client.get(
            reverse("core:prayer_times")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Prayer Times",
        )

    def test_ds_suggestions_require_two_characters(self):
        response = self.client.get(
            reverse("core:prayer_times_ds_suggestions"),
            {"q": "A"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["results"],
            [],
        )

    def test_ds_suggestions_return_matching_location(self):
        response = self.client.get(
            reverse("core:prayer_times_ds_suggestions"),
            {"q": "Akk"},
        )

        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["name_en"],
            "Akkaraipattu",
        )

    @patch(
        "core.views.get_prayer_times_for_coordinates",
        return_value=MOCK_PRAYER_DATA,
    )
    def test_current_location_api(self, mocked_service):
        response = self.client.post(
            reverse("core:prayer_times_current_api"),
            {
                "latitude": "7.218",
                "longitude": "81.849",
                "date": "2026-10-29",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        mocked_service.assert_called_once()

    @patch(
        "core.views.get_prayer_times_for_address",
        return_value=MOCK_PRAYER_DATA,
    )
    def test_ds_detail_page(self, mocked_service):
        response = self.client.get(
            reverse(
                "core:prayer_times_ds_detail",
                kwargs={"ds_id": self.ds.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Akkaraipattu",
        )
        self.assertContains(
            response,
            "04:58",
        )
        mocked_service.assert_called_once()

    @patch(
        "core.views._get_ds_prayer_times",
        return_value=(MOCK_PRAYER_DATA, False),
    )
    def test_ds_immediate_prayer_api(self, mocked_service):
        response = self.client.get(
            reverse(
                "core:prayer_times_ds_api",
                kwargs={"ds_id": self.ds.pk},
            ),
            {"date": "2026-10-29"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(
            payload["data"]["timings"]["Fajr"],
            "04:58",
        )
        self.assertEqual(
            payload["location"]["name_en"],
            "Akkaraipattu",
        )
        mocked_service.assert_called_once()
