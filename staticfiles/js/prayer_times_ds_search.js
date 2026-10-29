(() => {
    "use strict";

    const app = document.getElementById("dsPrayerSearchApp");
    const input = document.getElementById("dsPrayerSearchInput");
    const box = document.getElementById("dsPrayerSuggestions");
    const dateInput = document.getElementById("dsPrayerDate");
    const loading = document.getElementById("dsPrayerLoading");
    const errorBox = document.getElementById("dsPrayerError");
    const result = document.getElementById("dsPrayerResult");

    if (!app || !input || !box) return;

    const suggestionsUrl = app.dataset.suggestionsUrl;
    const apiTemplate = app.dataset.prayerApiTemplate;

    let timer = null;
    let controller = null;
    let prayerController = null;
    let activeIndex = -1;
    let selectedLocation = null;

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
        if (!errorBox) return;
        errorBox.textContent =
            message ||
            "Prayer times could not be loaded for this location.";
        errorBox.classList.remove("d-none");
    }

    function hideError() {
        errorBox?.classList.add("d-none");
        if (errorBox) errorBox.textContent = "";
    }

    function parseMinutes(value) {
        if (!value || !/^\d{1,2}:\d{2}$/.test(value)) return null;
        const [hour, minute] = value.split(":").map(Number);
        return (hour * 60) + minute;
    }

    function markNextPrayer(timings) {
        const rows = Array.from(
            result.querySelectorAll("[data-prayer-row]")
        );

        rows.forEach((row) => {
            row.classList.remove("is-next-prayer");
            const status = row.querySelector(".prayer-row-status");
            if (status) status.textContent = "";
        });

        const today = new Date();
        const selectedDate = dateInput?.value || "";
        const localDate = [
            today.getFullYear(),
            String(today.getMonth() + 1).padStart(2, "0"),
            String(today.getDate()).padStart(2, "0"),
        ].join("-");

        if (selectedDate !== localDate) return;

        const nowMinutes =
            (today.getHours() * 60) + today.getMinutes();

        const prayerOrder = [
            "Fajr",
            "Dhuhr",
            "Asr",
            "Maghrib",
            "Isha",
        ];

        const next = prayerOrder.find(
            (name) => {
                const mins = parseMinutes(timings?.[name]);
                return mins !== null && mins > nowMinutes;
            }
        );

        if (!next) return;

        const row = result.querySelector(
            `[data-prayer-row="${next}"]`
        );

        if (row) {
            row.classList.add("is-next-prayer");
            const status = row.querySelector(".prayer-row-status");
            if (status) status.textContent = "Next prayer";
        }
    }

    function renderPrayerTimes(payload) {
        const data = payload.data || {};
        const location = payload.location || {};
        const timings = data.timings || {};

        document.getElementById("dsPrayerLocationName").textContent =
            location.name || data.location_label || "Selected location";

        document.getElementById("dsPrayerLocationMeta").textContent =
            [location.district, location.province]
                .filter(Boolean)
                .join(" · ");

        document.getElementById("dsPrayerGregorianDate").textContent =
            data.date?.readable || "";

        document.getElementById("dsPrayerHijriDate").textContent =
            data.date?.hijri || "";

        for (const [name, value] of Object.entries(timings)) {
            const cell = result.querySelector(
                `[data-prayer-time="${name}"]`
            );

            if (cell) {
                cell.textContent = value || "--:--";
            }
        }

        document.getElementById("dsPrayerTimezone").textContent =
            data.meta?.timezone || "Asia/Colombo";

        document.getElementById("dsPrayerMethod").textContent =
            data.meta?.method || "Automatic";

        document.getElementById("dsPrayerCode").textContent =
            location.code || "—";

        document.getElementById("dsPrayerApproximate")
            ?.classList.toggle(
                "d-none",
                !payload.used_fallback
            );

        const fullPageLink =
            document.getElementById("dsPrayerFullPageLink");

        if (fullPageLink) {
            fullPageLink.href =
                `${location.detail_url || "#"}?date=${encodeURIComponent(
                    dateInput?.value || ""
                )}`;
        }

        markNextPrayer(timings);

        result.classList.remove("d-none");

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
            empty.textContent =
                "No matching Divisional Secretariat found";
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
                console.error("DS prayer search failed:", error);
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

    document.addEventListener("mousedown", (event) => {
        if (!app.contains(event.target)) {
            closeSuggestions();
        }
    });
})();
