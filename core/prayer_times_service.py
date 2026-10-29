import hashlib
import json
import time
from datetime import date, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.cache import cache
from django.utils import timezone


ALADHAN_API_BASE = "https://api.aladhan.com/v1"
ALADHAN_TIMEOUT_SECONDS = 6
ALADHAN_CACHE_SECONDS = 60 * 30

# Retry only transient provider/server failures.
ALADHAN_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
ALADHAN_RETRY_DELAYS = (0.4, 1.0)


class PrayerTimesError(Exception):
    """Raised when the prayer-times provider cannot return usable data."""


def _normalise_date(value=None):
    if value is None:
        return timezone.localdate()

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return datetime.strptime(
                value,
                "%Y-%m-%d",
            ).date()
        except ValueError as exc:
            raise PrayerTimesError(
                "Invalid date. Use YYYY-MM-DD."
            ) from exc

    raise PrayerTimesError("Invalid date value.")


def _provider_date(value=None):
    selected = _normalise_date(value)
    return selected.strftime("%d-%m-%Y")


def _clean_time(value):
    """
    AlAdhan may return a time with an annotation such as:
        04:58 (+0530)
    Keep only HH:MM.
    """
    if not value:
        return ""

    return str(value).strip().split(" ", 1)[0]


def _decode_provider_response(response):
    payload = json.loads(
        response.read().decode("utf-8")
    )

    if payload.get("code") != 200 or not payload.get("data"):
        raise PrayerTimesError(
            "Prayer times could not be calculated for this location."
        )

    return payload["data"]


def _request_json(endpoint, params):
    """
    Request AlAdhan JSON with retry support for transient HTTP errors.

    A 503 from AlAdhan means the provider is temporarily unavailable.
    We retry a small number of times before allowing the caller to use
    an alternate AlAdhan endpoint.
    """
    query = urlencode(params)
    url = f"{ALADHAN_API_BASE}/{endpoint}?{query}"

    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "User-Agent": (
                "MosquesSriLanka/1.0 "
                "(https://mosques.lk; prayer-times integration)"
            ),
        },
    )

    attempts = 1 + len(ALADHAN_RETRY_DELAYS)
    last_error = None

    for attempt in range(attempts):
        try:
            with urlopen(
                request,
                timeout=ALADHAN_TIMEOUT_SECONDS,
            ) as response:
                return _decode_provider_response(response)

        except HTTPError as exc:
            last_error = exc

            # Retry only server/rate-limit failures.
            if (
                exc.code not in ALADHAN_RETRYABLE_STATUS_CODES
                or attempt >= attempts - 1
            ):
                break

        except (
            URLError,
            TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            last_error = exc

            if attempt >= attempts - 1:
                break

        if attempt < len(ALADHAN_RETRY_DELAYS):
            time.sleep(ALADHAN_RETRY_DELAYS[attempt])

    raise PrayerTimesError(
        "Prayer times are temporarily unavailable from the provider."
    ) from last_error


def _normalise_payload(data, location_label, precision="exact"):
    timings = data.get("timings") or {}
    date_data = data.get("date") or {}
    hijri = date_data.get("hijri") or {}
    meta = data.get("meta") or {}

    method = meta.get("method") or {}
    method_name = (
        method.get("name")
        if isinstance(method, dict)
        else str(method or "")
    )

    return {
        "location_label": location_label,
        "precision": precision,
        "timings": {
            "Fajr": _clean_time(timings.get("Fajr")),
            "Sunrise": _clean_time(timings.get("Sunrise")),
            "Dhuhr": _clean_time(timings.get("Dhuhr")),
            "Asr": _clean_time(timings.get("Asr")),
            "Maghrib": _clean_time(timings.get("Maghrib")),
            "Isha": _clean_time(timings.get("Isha")),
        },
        "date": {
            "readable": date_data.get("readable", ""),
            "gregorian": (
                (date_data.get("gregorian") or {}).get("date", "")
            ),
            "hijri": hijri.get("date", ""),
            "hijri_day": hijri.get("day", ""),
            "hijri_month": (
                (hijri.get("month") or {}).get("en", "")
                if isinstance(hijri.get("month"), dict)
                else ""
            ),
            "hijri_year": hijri.get("year", ""),
        },
        "meta": {
            "timezone": meta.get("timezone", ""),
            "method": method_name or "Automatic",
        },
    }


def _calendar_day_from_payload(days, selected_date):
    """
    Extract one day from an AlAdhan monthly calendar response.
    """
    selected = _normalise_date(selected_date)
    target_provider_date = selected.strftime("%d-%m-%Y")

    if not isinstance(days, list):
        raise PrayerTimesError(
            "Prayer calendar response was not in the expected format."
        )

    for day in days:
        gregorian_date = (
            ((day or {}).get("date") or {})
            .get("gregorian", {})
            .get("date", "")
        )

        if gregorian_date == target_provider_date:
            return day

    # Defensive fallback: AlAdhan monthly arrays normally contain every day
    # in order, so the day number can be used if date matching is unavailable.
    day_index = selected.day - 1
    if 0 <= day_index < len(days):
        return days[day_index]

    raise PrayerTimesError(
        "The selected prayer date was not found in the provider calendar."
    )


def _calendar_fallback_coordinates(
    latitude,
    longitude,
    selected_date,
):
    selected = _normalise_date(selected_date)

    data = _request_json(
        f"calendar/{selected.year}/{selected.month}",
        {
            "latitude": latitude,
            "longitude": longitude,
            "iso8601": "false",
        },
    )

    return _calendar_day_from_payload(
        data,
        selected,
    )


def _calendar_fallback_address(
    address,
    selected_date,
    *,
    timezone_name=None,
):
    selected = _normalise_date(selected_date)

    params = {
        "address": address,
        "iso8601": "false",
    }

    if timezone_name:
        params["timezonestring"] = timezone_name

    data = _request_json(
        f"calendarByAddress/{selected.year}/{selected.month}",
        params,
    )

    return _calendar_day_from_payload(
        data,
        selected,
    )


def _calendar_fallback_city(
    city,
    country,
    selected_date,
    *,
    timezone_name=None,
):
    selected = _normalise_date(selected_date)

    params = {
        "city": city,
        "country": country,
        "iso8601": "false",
    }

    if timezone_name:
        params["timezonestring"] = timezone_name

    data = _request_json(
        f"calendarByCity/{selected.year}/{selected.month}",
        params,
    )

    return _calendar_day_from_payload(
        data,
        selected,
    )


def get_prayer_times_for_coordinates(
    latitude,
    longitude,
    selected_date=None,
):
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError) as exc:
        raise PrayerTimesError(
            "Invalid location coordinates."
        ) from exc

    if not -90 <= latitude <= 90:
        raise PrayerTimesError("Invalid latitude.")

    if not -180 <= longitude <= 180:
        raise PrayerTimesError("Invalid longitude.")

    selected = _normalise_date(selected_date)
    provider_date = selected.strftime("%d-%m-%Y")

    rounded_lat = round(latitude, 3)
    rounded_lon = round(longitude, 3)

    cache_key = (
        f"prayer-times:coords:"
        f"{provider_date}:{rounded_lat}:{rounded_lon}"
    )

    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        data = _request_json(
            f"timings/{provider_date}",
            {
                "latitude": latitude,
                "longitude": longitude,
                "iso8601": "false",
            },
        )
    except PrayerTimesError:
        # Alternate AlAdhan path: monthly coordinate calendar.
        data = _calendar_fallback_coordinates(
            latitude,
            longitude,
            selected,
        )

    result = _normalise_payload(
        data,
        "Current location",
        precision="coordinates",
    )

    cache.set(
        cache_key,
        result,
        ALADHAN_CACHE_SECONDS,
    )

    return result


def get_prayer_times_for_address(
    address,
    selected_date=None,
    *,
    timezone_name=None,
    location_label=None,
    precision="address",
):
    address = (address or "").strip()

    if not address or len(address) > 300:
        raise PrayerTimesError("Invalid location address.")

    selected = _normalise_date(selected_date)
    provider_date = selected.strftime("%d-%m-%Y")

    digest = hashlib.sha256(
        f"{provider_date}|{address}|{timezone_name or ''}".encode("utf-8")
    ).hexdigest()[:24]

    cache_key = f"prayer-times:address:{digest}"

    cached = cache.get(cache_key)
    if cached:
        return cached

    params = {
        "address": address,
        "iso8601": "false",
    }

    if timezone_name:
        params["timezonestring"] = timezone_name

    try:
        data = _request_json(
            f"timingsByAddress/{provider_date}",
            params,
        )
    except PrayerTimesError:
        # Alternate AlAdhan path: monthly address calendar.
        data = _calendar_fallback_address(
            address,
            selected,
            timezone_name=timezone_name,
        )

    result = _normalise_payload(
        data,
        location_label or address,
        precision=precision,
    )

    cache.set(
        cache_key,
        result,
        ALADHAN_CACHE_SECONDS,
    )

    return result


def get_prayer_times_for_city(
    city,
    country="Sri Lanka",
    selected_date=None,
    *,
    timezone_name=None,
    location_label=None,
    precision="city",
):
    city = (city or "").strip()
    country = (country or "").strip()

    if not city or len(city) > 180:
        raise PrayerTimesError("Invalid city or district name.")

    if not country or len(country) > 120:
        raise PrayerTimesError("Invalid country name.")

    selected = _normalise_date(selected_date)
    provider_date = selected.strftime("%d-%m-%Y")

    digest = hashlib.sha256(
        (
            f"{provider_date}|{city}|{country}|"
            f"{timezone_name or ''}"
        ).encode("utf-8")
    ).hexdigest()[:24]

    cache_key = f"prayer-times:city:{digest}"

    cached = cache.get(cache_key)
    if cached:
        return cached

    params = {
        "city": city,
        "country": country,
        "iso8601": "false",
    }

    if timezone_name:
        params["timezonestring"] = timezone_name

    try:
        data = _request_json(
            f"timingsByCity/{provider_date}",
            params,
        )
    except PrayerTimesError:
        # Alternate AlAdhan path: monthly city calendar.
        data = _calendar_fallback_city(
            city,
            country,
            selected,
            timezone_name=timezone_name,
        )

    result = _normalise_payload(
        data,
        location_label or f"{city}, {country}",
        precision=precision,
    )

    cache.set(
        cache_key,
        result,
        ALADHAN_CACHE_SECONDS,
    )

    return result
