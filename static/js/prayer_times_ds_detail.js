(() => {
    "use strict";

    const dataElement = document.getElementById("manualPrayerData");
    const result = document.getElementById("prayerTimesResult");

    if (!dataElement || !result) return;

    const timezone =
        dataElement.dataset.timezone || "Asia/Colombo";

    const selectedDate =
        dataElement.dataset.selectedDate || "";

    const timings = {
        Fajr: dataElement.dataset.fajr || "",
        Sunrise: dataElement.dataset.sunrise || "",
        Dhuhr: dataElement.dataset.dhuhr || "",
        Asr: dataElement.dataset.asr || "",
        Maghrib: dataElement.dataset.maghrib || "",
        Isha: dataElement.dataset.isha || "",
    };

    const PRAYER_ORDER = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"];

    function formatPrayerTime(value) {
        if (!value || !/^\d{1,2}:\d{2}$/.test(value)) {
            return value || "--:--";
        }

        const [hourRaw, minute] = value.split(":");
        const hour = Number(hourRaw);
        const period = hour >= 12 ? "PM" : "AM";
        const hour12 = hour % 12 || 12;

        return `${hour12}:${minute} ${period}`;
    }

    function prayerTimeToSeconds(value) {
        if (!value || !/^\d{1,2}:\d{2}$/.test(value)) {
            return null;
        }

        const [hours, minutes] = value.split(":").map(Number);
        return (hours * 3600) + (minutes * 60);
    }

    function timezoneParts() {
        const now = new Date();

        try {
            const formatter = new Intl.DateTimeFormat(
                document.documentElement.lang || "en",
                {
                    timeZone: timezone,
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

    function localIsoDate() {
        const parts = timezoneParts();

        return [
            parts.year,
            String(parts.month).padStart(2, "0"),
            String(parts.day).padStart(2, "0"),
        ].join("-");
    }

    function formatTime() {
        try {
            return new Intl.DateTimeFormat(
                document.documentElement.lang || "en",
                {
                    timeZone: timezone,
                    hour: "numeric",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: true,
                }
            ).format(new Date());
        } catch (error) {
            return new Date().toLocaleTimeString();
        }
    }

    function formatDate() {
        try {
            return new Intl.DateTimeFormat(
                document.documentElement.lang || "en",
                {
                    timeZone: timezone,
                    weekday: "long",
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                }
            ).format(new Date());
        } catch (error) {
            return new Date().toLocaleDateString();
        }
    }

    function formatCountdown(totalSeconds) {
        const safe = Math.max(0, Math.floor(totalSeconds));

        return [
            String(Math.floor(safe / 3600)).padStart(2, "0"),
            String(Math.floor((safe % 3600) / 60)).padStart(2, "0"),
            String(safe % 60).padStart(2, "0"),
        ].join(":");
    }

    function clearHighlights() {
        result.querySelectorAll("[data-prayer-row]").forEach((row) => {
            row.classList.remove("is-next-prayer");

            const status = row.querySelector(".prayer-auto-row-status");
            if (status) status.textContent = "";
        });
    }

    function findNextPrayer() {
        if (selectedDate !== localIsoDate()) {
            return null;
        }

        const now = timezoneParts();
        const nowSeconds =
            (now.hour * 3600) +
            (now.minute * 60) +
            now.second;

        for (const name of PRAYER_ORDER) {
            const seconds = prayerTimeToSeconds(timings[name]);

            if (seconds !== null && seconds > nowSeconds) {
                return {
                    name,
                    time: timings[name],
                    secondsRemaining: seconds - nowSeconds,
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

    function update() {
        document.getElementById("prayerCurrentTime").textContent =
            formatTime();

        document.getElementById("prayerCurrentDate").textContent =
            formatDate();

        clearHighlights();

        const next = findNextPrayer();

        if (!next) {
            document.getElementById("prayerNextName").textContent =
                "Selected date";
            document.getElementById("prayerNextTime").textContent =
                selectedDate || "—";
            document.getElementById("prayerNextCountdown").textContent =
                "—";
            return;
        }

        document.getElementById("prayerNextName").textContent =
            next.tomorrow
                ? `${next.name} · Tomorrow`
                : next.name;

        document.getElementById("prayerNextTime").textContent =
            formatPrayerTime(next.time);

        document.getElementById("prayerNextCountdown").textContent =
            formatCountdown(next.secondsRemaining);

        const row = result.querySelector(
            `[data-prayer-row="${next.name}"]`
        );

        if (row) {
            row.classList.add("is-next-prayer");

            const status = row.querySelector(".prayer-auto-row-status");
            if (status) {
                status.textContent =
                    next.tomorrow
                        ? "Next prayer tomorrow"
                        : "Next prayer";
            }
        }
    }

    // Format the rendered prayer-time cells to 12-hour display.
    for (const [name, value] of Object.entries(timings)) {
        const cell = result.querySelector(`[data-prayer="${name}"]`);
        if (cell) {
            cell.textContent = formatPrayerTime(value);
        }
    }

    update();
    window.setInterval(update, 1000);
})();
