(() => {
    "use strict";

    const form = document.getElementById("mosqueDirectorySearchForm");
    const input = document.getElementById("directoryMosqueQuery");

    if (!form || !input) return;

    const directoryUrl = form.dataset.directoryUrl;
    if (!directoryUrl) return;

    const province = document.getElementById("directoryProvince");
    const district = document.getElementById("directoryDistrict");
    const ds = document.getElementById("directoryDS");
    const gn = document.getElementById("directoryGN");

    const MIN_CHARS = 2;
    const DEBOUNCE_MS = 180;

    let timer = null;
    let controller = null;
    let activeIndex = -1;

    const wrapper = input.closest(".directory-main-search");
    if (!wrapper) return;

    const box = document.createElement("div");
    box.className = "main-mosque-autocomplete";
    box.setAttribute("role", "listbox");
    box.hidden = true;
    wrapper.appendChild(box);

    function closeSuggestions() {
        box.hidden = true;
        box.innerHTML = "";
        activeIndex = -1;
        input.setAttribute("aria-expanded", "false");
        input.removeAttribute("aria-activedescendant");
    }

    function selectedValue(select) {
        return select && !select.disabled ? select.value : "";
    }

    function buildUrl(query) {
        const params = new URLSearchParams({
            autocomplete: "1",
            q: query,
        });

        const provinceValue = selectedValue(province);
        const districtValue = selectedValue(district);
        const dsValue = selectedValue(ds);
        const gnValue = selectedValue(gn);

        if (provinceValue) {
            params.set("province", provinceValue);
        }

        if (districtValue) {
            params.set("district", districtValue);
        }

        if (dsValue) {
            params.set("divisional_secretariat", dsValue);
        }

        if (gnValue) {
            params.set("gn_division", gnValue);
        }

        return `${directoryUrl}?${params.toString()}`;
    }

    function suggestionItems() {
        return Array.from(
            box.querySelectorAll(".main-mosque-autocomplete-item")
        );
    }

    function setActive(index) {
        const items = suggestionItems();
        if (!items.length) return;

        activeIndex = (index + items.length) % items.length;

        items.forEach((item, itemIndex) => {
            const isActive = itemIndex === activeIndex;

            item.classList.toggle("is-active", isActive);
            item.setAttribute(
                "aria-selected",
                isActive ? "true" : "false"
            );
        });

        const item = items[activeIndex];

        input.setAttribute(
            "aria-activedescendant",
            item.id
        );

        item.scrollIntoView({
            block: "nearest",
        });
    }

    function choose(item) {
        input.value = item.dataset.value || "";
        closeSuggestions();
        input.focus();
    }

    function render(results) {
        box.innerHTML = "";
        activeIndex = -1;

        if (!results.length) {
            const empty = document.createElement("div");
            empty.className = "main-mosque-autocomplete-empty";
            empty.textContent = "No matching approved mosques found";
            box.appendChild(empty);

            box.hidden = false;
            input.setAttribute("aria-expanded", "true");
            return;
        }

        results.forEach((result, index) => {
            const item = document.createElement("button");

            item.type = "button";
            item.className = "main-mosque-autocomplete-item";
            item.id = `main-mosque-suggestion-${index}`;
            item.dataset.value = result.value || result.name || "";
            item.setAttribute("role", "option");
            item.setAttribute("aria-selected", "false");

            const icon = document.createElement("span");
            icon.className = "main-mosque-autocomplete-icon";
            icon.innerHTML = '<i class="bi bi-moon-stars"></i>';

            const body = document.createElement("span");
            body.className = "main-mosque-autocomplete-body";

            const top = document.createElement("span");
            top.className = "main-mosque-autocomplete-top";

            const title = document.createElement("strong");
            title.textContent = result.name || "";

            const code = document.createElement("small");
            code.textContent = result.mosque_id || "";

            top.append(title, code);

            const location = document.createElement("span");
            location.className = "main-mosque-autocomplete-location";
            location.textContent = result.location || "";

            body.append(top, location);
            item.append(icon, body);

            item.addEventListener("mousedown", (event) => {
                event.preventDefault();
            });

            item.addEventListener("click", () => {
                choose(item);
            });

            box.appendChild(item);
        });

        box.hidden = false;
        input.setAttribute("aria-expanded", "true");
    }

    async function fetchSuggestions() {
        const query = input.value.trim();

        if (query.length < MIN_CHARS) {
            closeSuggestions();
            return;
        }

        if (controller) {
            controller.abort();
        }

        controller = new AbortController();

        try {
            const response = await fetch(
                buildUrl(query),
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
            if (error.name === "AbortError") {
                return;
            }

            console.error(
                "Main mosque autocomplete failed:",
                error
            );

            closeSuggestions();
        }
    }

    input.addEventListener("input", () => {
        window.clearTimeout(timer);

        timer = window.setTimeout(
            fetchSuggestions,
            DEBOUNCE_MS
        );
    });

    input.addEventListener("focus", () => {
        if (input.value.trim().length >= MIN_CHARS) {
            fetchSuggestions();
        }
    });

    input.addEventListener("keydown", (event) => {
        const items = suggestionItems();

        if (event.key === "Escape") {
            closeSuggestions();
            return;
        }

        if (!items.length) return;

        if (event.key === "ArrowDown") {
            event.preventDefault();
            setActive(activeIndex + 1);
            return;
        }

        if (event.key === "ArrowUp") {
            event.preventDefault();
            setActive(
                activeIndex <= 0
                    ? items.length - 1
                    : activeIndex - 1
            );
            return;
        }

        if (
            event.key === "Enter" &&
            activeIndex >= 0
        ) {
            event.preventDefault();
            choose(items[activeIndex]);
        }
    });

    document.addEventListener("mousedown", (event) => {
        if (!wrapper.contains(event.target)) {
            closeSuggestions();
        }
    });
})();
