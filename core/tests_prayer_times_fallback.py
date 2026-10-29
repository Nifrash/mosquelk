from django.test import SimpleTestCase

from core.views import (
    SRI_LANKA_PROVINCE_COORDINATES,
    _normalise_province_name,
)


class PrayerTimesProvinceFallbackTests(SimpleTestCase):
    def test_all_nine_sri_lanka_provinces_have_coordinates(self):
        expected = {
            "central",
            "eastern",
            "north central",
            "north western",
            "northern",
            "sabaragamuwa",
            "southern",
            "uva",
            "western",
        }

        self.assertEqual(
            set(SRI_LANKA_PROVINCE_COORDINATES),
            expected,
        )

    def test_province_name_normalisation(self):
        self.assertEqual(
            _normalise_province_name("Eastern Province"),
            "eastern",
        )
        self.assertEqual(
            _normalise_province_name("Western"),
            "western",
        )
