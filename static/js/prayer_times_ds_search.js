(() => {
    "use strict";

    const app = document.getElementById("dsPrayerSearchApp");
    const input = document.getElementById("dsPrayerSearchInput");
    const box = document.getElementById("dsPrayerSuggestions");
    const dateInput = document.getElementById("dsPrayerDate");
    const loading = document.getElementById("dsPrayerLoading");
    const errorBox = document.getElementById("dsPrayerError");
    const result = document.getElementById("prayerTimesResult");

    if (!app || !input || !box || !result) return;

    const suggestionsUrl = app.dataset.suggestionsUrl;
    const apiTemplate = app.dataset.prayerApiTemplate;

    let timer = null;
    let controller = null;
    let prayerController = null;
    let activeIndex = -1;
    let selectedLocation = null;
    let liveTimer = null;
    let currentData = null;
    let currentTimezone = "Asia/Colombo";

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
            return new Date().toLocaleTimeString();
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
            return new Date().toLocaleDateString();
        }
    }

    function localIsoDate(timeZone) {
        const parts = timezoneParts(timeZone);

        return [
            parts.year,
            String(parts.month).padStart(2, "0"),
            String(parts.day).padStart(2, "0"),
        ].join("-");
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

    function clearHighlights() {
        result.querySelectorAll("[data-prayer-row]").forEach((row) => {
            row.classList.remove("is-next-prayer");

            const status = row.querySelector(".prayer-auto-row-status");
            if (status) status.textContent = "";
        });
    }

    function findNextPrayer() {
        if (!currentData) return null;

        if ((dateInput?.value || "") !== localIsoDate(currentTimezone)) {
            return null;
        }

        const now = timezoneParts(currentTimezone);
        const nowSeconds =
            (now.hour * 3600) +
            (now.minute * 60) +
            now.second;

        for (const name of PRAYER_ORDER) {
            const seconds = prayerTimeToSeconds(
                currentData.timings?.[name]
            );

            if (seconds !== null && seconds > nowSeconds) {
                return {
                    name,
                    time: currentData.timings[name],
                    secondsRemaining: seconds - nowSeconds,
                    tomorrow: false,
                };
            }
        }

        const fajrSeconds = prayerTimeToSeconds(
            currentData.timings?.Fajr
        );

        if (fajrSeconds !== null) {
            return {
                name: "Fajr",
                time: currentData.timings.Fajr,
                secondsRemaining:
                    (24 * 3600) - nowSeconds + fajrSeconds,
                tomorrow: true,
            };
        }

        return null;
    }

    function updateLiveDashboard() {
        if (!currentData) return;

        document.getElementById("prayerCurrentTime").textContent =
            formatCurrentTime(currentTimezone);

        document.getElementById("prayerCurrentDate").textContent =
            formatCurrentDate(currentTimezone);

        const next = findNextPrayer();
        clearHighlights();

        if (!next) {
            document.getElementById("prayerNextName").textContent =
                "Selected date";
            document.getElementById("prayerNextTime").textContent =
                dateInput?.value || "—";
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

    function startLiveClock() {
        if (liveTimer) {
            window.clearInterval(liveTimer);
        }

        updateLiveDashboard();
        liveTimer = window.setInterval(updateLiveDashboard, 1000);
    }

    function closeSuggestions() {
        box.hidden = true;
        box.innerHTML = "";
        activeIndex = -1;
        input.setAttribute("aria-expanded", "false");
        input.removeAttribute("aria-activedescendant");
    }

    function items() {
        return Array.from(
            box.querySelectorAll(".ds-prayer-suggestion")
        );
    }

    function setActive(index) {
        const all = items();
        if (!all.length) return;

        activeIndex = (index + all.length) % all.length;

        all.forEach((item, i) => {
            const active = i === activeIndex;
            item.classList.toggle("is-active", active);
            item.setAttribute("aria-selected", active ? "true" : "false");
        });

        const current = all[activeIndex];
        input.setAttribute("aria-activedescendant", current.id);
        current.scrollIntoView({block: "nearest"});
    }

    function buildPrayerApiUrl(dsId) {
        const path = apiTemplate.replace("999999", String(dsId));
        const params = new URLSearchParams();

        if (dateInput?.value) {
            params.set("date", dateInput.value);
        }

        return `${path}?${params.toString()}`;
    }

    function setLoading(isLoading) {
        loading?.classList.toggle("d-none", !isLoading);
    }

    function showError(message) {
        errorBox.textContent =
            message ||
            "Prayer times could not be loaded for this location.";
        errorBox.classList.remove("d-none");
    }

    function hideError() {
        errorBox.classList.add("d-none");
        errorBox.textContent = "";
    }

    function renderPrayerTimes(payload) {
        const data = payload.data || {};
        const location = payload.location || {};
        const timings = data.timings || {};

        currentData = data;
        currentTimezone =
            data.meta?.timezone || "Asia/Colombo";

        document.getElementById("prayerResultLocation").textContent =
            location.name ||
            data.location_label ||
            "Selected location";

        document.getElementById("prayerLocationAccuracy").textContent =
            [location.district, location.province]
                .filter(Boolean)
                .join(" · ");

        document.getElementById("prayerTimezone").textContent =
            currentTimezone;

        document.getElementById("prayerGregorianDate").textContent =
            data.date?.readable ||
            data.date?.gregorian ||
            "—";

        document.getElementById("prayerHijriDate").textContent =
            data.date?.hijri || "—";

        document.getElementById("prayerMethod").textContent =
            data.meta?.method || "Automatic";

        document.getElementById("prayerLastUpdated").textContent =
            formatCurrentTime(currentTimezone);

        document.getElementById("prayerSuhoorEnds").textContent =
            formatPrayerTime(timings.Fajr);

        document.getElementById("prayerIftarTime").textContent =
            formatPrayerTime(timings.Maghrib);

        for (const [name, value] of Object.entries(timings)) {
            const cell = result.querySelector(
                `[data-prayer="${name}"]`
            );

            if (cell) {
                cell.textContent = formatPrayerTime(value);
            }
        }

        document.getElementById("dsPrayerApproximate")
            ?.classList.toggle(
                "d-none",
                !payload.used_fallback
            );

        const fullPageLink =
            document.getElementById("prayerDedicatedPageLink");

        if (fullPageLink) {
            fullPageLink.href =
                `${location.detail_url || "#"}?date=${encodeURIComponent(
                    dateInput?.value || ""
                )}`;
        }

        result.classList.remove("d-none");
        startLiveClock();

        result.scrollIntoView({
            behavior: "smooth",
            block: "start",
        });
    }

    async function loadPrayerTimes(dsId) {
        if (!dsId) return;

        hideError();
        setLoading(true);

        if (prayerController) {
            prayerController.abort();
        }

        prayerController = new AbortController();

        try {
            const response = await fetch(
                buildPrayerApiUrl(dsId),
                {
                    signal: prayerController.signal,
                    headers: {
                        "Accept": "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                }
            );

            const payload = await response.json();

            if (!response.ok || !payload.ok) {
                throw new Error(
                    payload.message ||
                    "Prayer times could not be loaded for this location."
                );
            }

            renderPrayerTimes(payload);
        } catch (error) {
            if (error.name === "AbortError") return;

            console.error("Prayer time loading failed:", error);

            result.classList.add("d-none");
            showError(error.message);
        } finally {
            setLoading(false);
        }
    }

    function choose(item) {
        const dsId = item.dataset.id;
        const dsName = item.dataset.name || "";

        input.value = dsName;

        selectedLocation = {
            id: dsId,
            name: dsName,
        };

        closeSuggestions();
        loadPrayerTimes(dsId);
    }

    function render(results) {
        box.innerHTML = "";
        activeIndex = -1;

        if (!results.length) {
            const empty = document.createElement("div");
            empty.className = "ds-prayer-suggestion-empty";
            empty.textContent = "No matching city or town found";
            box.appendChild(empty);
            box.hidden = false;
            input.setAttribute("aria-expanded", "true");
            return;
        }

        results.forEach((resultData, index) => {
            const item = document.createElement("button");
            item.type = "button";
            item.className = "ds-prayer-suggestion";
            item.id = `ds-prayer-suggestion-${index}`;
            item.dataset.id = String(resultData.id);
            item.dataset.name =
                resultData.name || resultData.name_en || "";
            item.setAttribute("role", "option");
            item.setAttribute("aria-selected", "false");

            item.innerHTML = `
                <span class="ds-prayer-suggestion-icon">
                    <i class="bi bi-geo-alt"></i>
                </span>
                <span class="ds-prayer-suggestion-copy">
                    <strong></strong>
                    <small></small>
                </span>
                <i class="bi bi-chevron-right"></i>
            `;

            item.querySelector("strong").textContent =
                resultData.name || resultData.name_en || "";

            item.querySelector("small").textContent =
                [
                    resultData.district,
                    resultData.province,
                    resultData.code,
                ].filter(Boolean).join(" · ");

            item.addEventListener("mousedown", (event) => {
                event.preventDefault();
            });

            item.addEventListener("click", () => choose(item));

            box.appendChild(item);
        });

        box.hidden = false;
        input.setAttribute("aria-expanded", "true");
    }

    async function search() {
        const query = input.value.trim();

        if (query.length < 2) {
            closeSuggestions();
            return;
        }

        if (controller) controller.abort();

        controller = new AbortController();

        try {
            const response = await fetch(
                `${suggestionsUrl}?q=${encodeURIComponent(query)}`,
                {
                    signal: controller.signal,
                    headers: {
                        "Accept": "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                }
            );

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const payload = await response.json();
            render(payload.results || []);
        } catch (error) {
            if (error.name !== "AbortError") {
                console.error("City/town prayer search failed:", error);
                closeSuggestions();
            }
        }
    }

    input.addEventListener("input", () => {
        selectedLocation = null;
        window.clearTimeout(timer);
        timer = window.setTimeout(search, 180);
    });

    input.addEventListener("keydown", (event) => {
        const all = items();

        if (event.key === "Escape") {
            closeSuggestions();
            return;
        }

        if (!all.length) return;

        if (event.key === "ArrowDown") {
            event.preventDefault();
            setActive(activeIndex + 1);
            return;
        }

        if (event.key === "ArrowUp") {
            event.preventDefault();
            setActive(
                activeIndex <= 0
                    ? all.length - 1
                    : activeIndex - 1
            );
            return;
        }

        if (event.key === "Enter" && activeIndex >= 0) {
            event.preventDefault();
            choose(all[activeIndex]);
        }
    });

    dateInput?.addEventListener("change", () => {
        if (selectedLocation?.id) {
            loadPrayerTimes(selectedLocation.id);
        }
    });

    document
        .getElementById("focusPrayerLocationSearch")
        ?.addEventListener("click", () => {
            input.focus();
            input.select();

            app.scrollIntoView({
                behavior: "smooth",
                block: "start",
            });
        });

    document.addEventListener("mousedown", (event) => {
        if (!app.contains(event.target)) {
            closeSuggestions();
        }
    });
})();
