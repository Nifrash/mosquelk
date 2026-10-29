(() => {
    "use strict";

    const app = document.getElementById("prayerTimesApp");
    if (!app) return;

    const apiUrl = app.dataset.apiUrl;
    const refreshButton = document.getElementById("refreshPrayerLocation");
    const statusCard = document.getElementById("prayerLocationStatus");
    const errorBox = document.getElementById("prayerTimesError");
    const resultBox = document.getElementById("prayerTimesResult");
    const manualFallback = document.getElementById("prayerManualFallback");
    const heroLocationState = document.getElementById("heroLocationState");

    const csrfInput = document.querySelector(
        "#prayerTimesCsrfForm input[name='csrfmiddlewaretoken']"
    );

    let detecting = false;
    let liveTimer = null;
    let currentPrayerData = null;
    let currentTimezone = null;
    let locationAccuracy = null;

    const PRAYER_ORDER = [
        "Fajr",
        "Dhuhr",
        "Asr",
        "Maghrib",
        "Isha",
    ];

    function setHeroState(text) {
        if (heroLocationState) {
            heroLocationState.textContent = text;
        }
    }

    function setStatus(title, text, icon = "bi-crosshair") {
        if (!statusCard) return;

        statusCard.classList.remove("d-none");

        statusCard.innerHTML = `
            <div class="prayer-status-icon">
                <i class="bi ${icon}"></i>
            </div>
            <div>
                <span class="prayer-section-label">Automatic Location</span>
                <h2>${title}</h2>
                <p>${text}</p>
            </div>
        `;
    }

    function showError(message) {
        if (!errorBox) return;

        errorBox.textContent = message;
        errorBox.classList.remove("d-none");
        manualFallback?.classList.remove("d-none");
    }

    function hideError() {
        if (!errorBox) return;

        errorBox.classList.add("d-none");
        errorBox.textContent = "";
    }

    function currentDeviceDate() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, "0");
        const day = String(now.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    function formatPrayerTime(value) {
        if (!value || !/^\d{1,2}:\d{2}$/.test(value)) {
            return value || "--:--";
        }

        const [hourRaw, minute] = value.split(":");
        const hour = Number(hourRaw);

        if (Number.isNaN(hour)) {
            return value;
        }

        const period = hour >= 12 ? "PM" : "AM";
        const hour12 = hour % 12 || 12;

        return `${hour12}:${minute} ${period}`;
    }

    function prayerTimeToSeconds(value) {
        if (!value || !/^\d{1,2}:\d{2}$/.test(value)) {
            return null;
        }

        const [hours, minutes] = value.split(":").map(Number);

        if (
            Number.isNaN(hours) ||
            Number.isNaN(minutes)
        ) {
            return null;
        }

        return (hours * 3600) + (minutes * 60);
    }

    function timezoneParts(timeZone) {
        const now = new Date();

        try {
            const formatter = new Intl.DateTimeFormat(
                document.documentElement.lang || "en",
                {
                    timeZone,
                    year: "numeric",
                    month: "2-digit",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hourCycle: "h23",
                }
            );

            const parts = Object.fromEntries(
                formatter
                    .formatToParts(now)
                    .filter((part) => part.type !== "literal")
                    .map((part) => [part.type, part.value])
            );

            return {
                year: Number(parts.year),
                month: Number(parts.month),
                day: Number(parts.day),
                hour: Number(parts.hour),
                minute: Number(parts.minute),
                second: Number(parts.second),
            };
        } catch (error) {
            return {
                year: now.getFullYear(),
                month: now.getMonth() + 1,
                day: now.getDate(),
                hour: now.getHours(),
                minute: now.getMinutes(),
                second: now.getSeconds(),
            };
        }
    }

    function formatCurrentTime(timeZone) {
        try {
            return new Intl.DateTimeFormat(
                document.documentElement.lang || "en",
                {
                    timeZone,
                    hour: "numeric",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: true,
                }
            ).format(new Date());
        } catch (error) {
            return new Intl.DateTimeFormat(
                document.documentElement.lang || "en",
                {
                    hour: "numeric",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: true,
                }
            ).format(new Date());
        }
    }

    function formatCurrentDate(timeZone) {
        try {
            return new Intl.DateTimeFormat(
                document.documentElement.lang || "en",
                {
                    timeZone,
                    weekday: "long",
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                }
            ).format(new Date());
        } catch (error) {
            return new Intl.DateTimeFormat(
                document.documentElement.lang || "en",
                {
                    weekday: "long",
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                }
            ).format(new Date());
        }
    }

    function formatCountdown(totalSeconds) {
        const safe = Math.max(0, Math.floor(totalSeconds));

        const hours = Math.floor(safe / 3600);
        const minutes = Math.floor((safe % 3600) / 60);
        const seconds = safe % 60;

        return [
            String(hours).padStart(2, "0"),
            String(minutes).padStart(2, "0"),
            String(seconds).padStart(2, "0"),
        ].join(":");
    }

    function findNextPrayer(data, timeZone) {
        const timings = data?.timings || {};
        const now = timezoneParts(timeZone);

        const nowSeconds =
            (now.hour * 3600) +
            (now.minute * 60) +
            now.second;

        for (const name of PRAYER_ORDER) {
            const prayerSeconds = prayerTimeToSeconds(timings[name]);

            if (
                prayerSeconds !== null &&
                prayerSeconds > nowSeconds
            ) {
                return {
                    name,
                    time: timings[name],
                    secondsRemaining:
                        prayerSeconds - nowSeconds,
                    tomorrow: false,
                };
            }
        }

        const fajrSeconds = prayerTimeToSeconds(timings.Fajr);

        if (fajrSeconds !== null) {
            return {
                name: "Fajr",
                time: timings.Fajr,
                secondsRemaining:
                    (24 * 3600) - nowSeconds + fajrSeconds,
                tomorrow: true,
            };
        }

        return null;
    }

    function clearPrayerHighlights() {
        resultBox
            ?.querySelectorAll("[data-prayer-row]")
            .forEach((row) => {
                row.classList.remove("is-next-prayer");

                const status = row.querySelector(
                    ".prayer-auto-row-status"
                );

                if (status) {
                    status.textContent = "";
                }
            });
    }

    function updateLiveDashboard() {
        if (!currentPrayerData) return;

        const timeZone =
            currentTimezone ||
            currentPrayerData.meta?.timezone ||
            Intl.DateTimeFormat().resolvedOptions().timeZone;

        const currentTimeElement =
            document.getElementById("prayerCurrentTime");

        const currentDateElement =
            document.getElementById("prayerCurrentDate");

        if (currentTimeElement) {
            currentTimeElement.textContent =
                formatCurrentTime(timeZone);
        }

        if (currentDateElement) {
            currentDateElement.textContent =
                formatCurrentDate(timeZone);
        }

        const next = findNextPrayer(
            currentPrayerData,
            timeZone
        );

        clearPrayerHighlights();

        if (!next) return;

        const nextName = document.getElementById(
            "prayerNextName"
        );
        const nextTime = document.getElementById(
            "prayerNextTime"
        );
        const countdown = document.getElementById(
            "prayerNextCountdown"
        );

        if (nextName) {
            nextName.textContent =
                next.tomorrow
                    ? `${next.name} · Tomorrow`
                    : next.name;
        }

        if (nextTime) {
            nextTime.textContent =
                formatPrayerTime(next.time);
        }

        if (countdown) {
            countdown.textContent =
                formatCountdown(next.secondsRemaining);
        }

        const nextRow = resultBox?.querySelector(
            `[data-prayer-row="${next.name}"]`
        );

        if (nextRow) {
            nextRow.classList.add("is-next-prayer");

            const status = nextRow.querySelector(
                ".prayer-auto-row-status"
            );

            if (status) {
                status.textContent =
                    next.tomorrow
                        ? "Next prayer tomorrow"
                        : "Next prayer";
            }
        }
    }

    function startLiveClock() {
        if (liveTimer) {
            window.clearInterval(liveTimer);
        }

        updateLiveDashboard();

        liveTimer = window.setInterval(
            updateLiveDashboard,
            1000
        );
    }

    function renderPrayerTimes(data) {
        currentPrayerData = data;
        currentTimezone =
            data.meta?.timezone ||
            Intl.DateTimeFormat().resolvedOptions().timeZone;

        resultBox?.classList.remove("d-none");
        statusCard?.classList.add("d-none");
        manualFallback?.classList.add("d-none");

        setHeroState("Location detected · Prayer timetable ready");

        const locationElement = document.getElementById(
            "prayerResultLocation"
        );

        if (locationElement) {
            locationElement.textContent =
                data.location_label === "Current location"
                    ? "Your Current Location"
                    : (data.location_label || "Your Current Location");
        }

        const accuracyElement = document.getElementById(
            "prayerLocationAccuracy"
        );

        if (accuracyElement) {
            if (
                locationAccuracy &&
                Number.isFinite(locationAccuracy)
            ) {
                if (locationAccuracy < 1000) {
                    accuracyElement.textContent =
                        `Location accuracy about ${Math.round(locationAccuracy)} m`;
                } else {
                    accuracyElement.textContent =
                        `Location accuracy about ${(locationAccuracy / 1000).toFixed(1)} km`;
                }
            } else {
                accuracyElement.textContent =
                    "Location detected";
            }
        }

        for (
            const [name, value]
            of Object.entries(data.timings || {})
        ) {
            const element = resultBox?.querySelector(
                `[data-prayer="${name}"]`
            );

            if (element) {
                element.textContent =
                    formatPrayerTime(value);
            }
        }

        const timezoneElement =
            document.getElementById("prayerTimezone");

        const methodElement =
            document.getElementById("prayerMethod");

        const gregorianElement =
            document.getElementById("prayerGregorianDate");

        const hijriElement =
            document.getElementById("prayerHijriDate");

        const lastUpdatedElement =
            document.getElementById("prayerLastUpdated");

        if (timezoneElement) {
            timezoneElement.textContent =
                currentTimezone || "—";
        }

        if (methodElement) {
            methodElement.textContent =
                data.meta?.method || "Automatic";
        }

        if (gregorianElement) {
            gregorianElement.textContent =
                data.date?.readable ||
                data.date?.gregorian ||
                "—";
        }

        if (hijriElement) {
            hijriElement.textContent =
                data.date?.hijri || "—";
        }

        if (lastUpdatedElement) {
            lastUpdatedElement.textContent =
                formatCurrentTime(currentTimezone);
        }

        const suhoorElement =
            document.getElementById("prayerSuhoorEnds");

        const iftarElement =
            document.getElementById("prayerIftarTime");

        if (suhoorElement) {
            suhoorElement.textContent =
                formatPrayerTime(data.timings?.Fajr);
        }

        if (iftarElement) {
            iftarElement.textContent =
                formatPrayerTime(data.timings?.Maghrib);
        }

        startLiveClock();

        resultBox?.scrollIntoView({
            behavior: "smooth",
            block: "start",
        });
    }

    async function requestPrayerTimes(
        latitude,
        longitude
    ) {
        const body = new URLSearchParams({
            latitude: String(latitude),
            longitude: String(longitude),
            date: currentDeviceDate(),
            csrfmiddlewaretoken:
                csrfInput?.value || "",
        });

        const response = await fetch(
            apiUrl,
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/x-www-form-urlencoded;charset=UTF-8",
                    "X-CSRFToken":
                        csrfInput?.value || "",
                    "Accept": "application/json",
                },
                body: body.toString(),
            }
        );

        let payload;

        try {
            payload = await response.json();
        } catch (error) {
            throw new Error(
                "Prayer times could not be loaded. Please try again or choose your city or town."
            );
        }

        if (!response.ok || !payload.ok) {
            throw new Error(
                payload.message ||
                "Prayer times are temporarily unavailable."
            );
        }

        return payload.data;
    }

    function detectLocation() {
        if (detecting) return;

        hideError();
        resultBox?.classList.add("d-none");

        if (liveTimer) {
            window.clearInterval(liveTimer);
            liveTimer = null;
        }

        if (!navigator.geolocation) {
            setHeroState("Automatic location is unavailable");

            setStatus(
                "Automatic location is not available",
                "This browser cannot provide your current location. Please select your city or town manually.",
                "bi-geo-alt"
            );

            manualFallback?.classList.remove("d-none");
            return;
        }

        detecting = true;

        setHeroState("Detecting your location automatically...");

        setStatus(
            "Finding your current location",
            "Please allow location access if your browser asks. The timetable will appear automatically once your location is detected.",
            "bi-crosshair"
        );

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                locationAccuracy =
                    position.coords.accuracy;

                setHeroState(
                    "Location detected · Loading prayer times..."
                );

                setStatus(
                    "Location detected",
                    "Your location was found successfully. We are loading today's prayer timetable.",
                    "bi-check-circle"
                );

                try {
                    const data =
                        await requestPrayerTimes(
                            position.coords.latitude,
                            position.coords.longitude
                        );

                    renderPrayerTimes(data);
                } catch (error) {
                    setHeroState(
                        "Choose your city or town manually"
                    );

                    setStatus(
                        "Could not load prayer times automatically",
                        "Your location was detected, but the prayer-time service could not return a result. Please choose your city or town manually.",
                        "bi-exclamation-triangle"
                    );

                    showError(error.message);
                } finally {
                    detecting = false;
                }
            },
            (error) => {
                detecting = false;

                let message =
                    "We could not access your current location. Please choose your city or town manually.";

                if (
                    error.code ===
                    error.PERMISSION_DENIED
                ) {
                    message =
                        "Location permission was not granted. You can still select your city or town manually.";
                } else if (
                    error.code ===
                    error.POSITION_UNAVAILABLE
                ) {
                    message =
                        "Your current position is unavailable. Please select your city or town manually.";
                } else if (
                    error.code ===
                    error.TIMEOUT
                ) {
                    message =
                        "Location detection took too long. Please try again or select your city or town manually.";
                }

                setHeroState(
                    "Choose your city or town manually"
                );

                setStatus(
                    "Select your location manually",
                    message,
                    "bi-geo-alt"
                );

                manualFallback?.classList.remove("d-none");
            },
            {
                enableHighAccuracy: false,
                timeout: 10000,
                maximumAge: 300000,
            }
        );
    }

    refreshButton?.addEventListener(
        "click",
        detectLocation
    );

    // Core requested behaviour:
    // immediately attempt browser geolocation as soon as the page loads.
    detectLocation();
})();
