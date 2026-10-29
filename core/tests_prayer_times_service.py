from unittest.mock import patch

from django.test import SimpleTestCase

from core.prayer_times_service import (
    PrayerTimesError,
    _calendar_day_from_payload,
    get_prayer_times_for_city,
)


DAILY_DATA = {
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
        "gregorian": {"date": "29-10-2026"},
        "hijri": {
            "date": "17-05-1448",
            "day": "17",
            "month": {"en": "Jumada al-awwal"},
            "year": "1448",
        },
    },
    "meta": {
        "timezone": "Asia/Colombo",
        "method": {"name": "Automatic"},
    },
}


class PrayerTimesServiceReliabilityTests(SimpleTestCase):
    def test_calendar_day_extracts_selected_date(self):
        days = [
            {
                "timings": {"Fajr": "04:59"},
                "date": {
                    "gregorian": {"date": "28-10-2026"},
                },
                "meta": {},
            },
            DAILY_DATA,
        ]

        day = _calendar_day_from_payload(
            days,
            "2026-10-29",
        )

        self.assertEqual(
            day["timings"]["Fajr"],
            "04:58",
        )

    @patch(
        "core.prayer_times_service._calendar_fallback_city",
        return_value=DAILY_DATA,
    )
    @patch(
        "core.prayer_times_service._request_json",
        side_effect=PrayerTimesError(
            "Prayer times are temporarily unavailable."
        ),
    )
    def test_city_uses_monthly_fallback_when_daily_fails(
        self,
        mocked_daily,
        mocked_calendar,
    ):
        result = get_prayer_times_for_city(
            "Ampara",
            "Sri Lanka",
            "2026-10-29",
            timezone_name="Asia/Colombo",
        )

        self.assertEqual(
            result["timings"]["Fajr"],
            "04:58",
        )
        mocked_daily.assert_called_once()
        mocked_calendar.assert_called_once()
