(() => {
    "use strict";

    const form = document.getElementById("mosqueDirectorySearchForm");
    if (!form) return;

    const province = document.getElementById("directoryProvince");
    const district = document.getElementById("directoryDistrict");
    const ds = document.getElementById("directoryDS");
    const gn = document.getElementById("directoryGN");

    const districtApi = form.dataset.districtApi;
    const dsApi = form.dataset.dsApi;
    const gnApi = form.dataset.gnApi;

    const searchInputs = Array.from(
        form.querySelectorAll("[data-option-search]")
    );

    const MIN_AUTOCOMPLETE_CHARS = 2;
    const MAX_SUGGESTIONS = 8;

    function findSearchInput(select) {
        return searchInputs.find(
            (input) => input.dataset.optionSearch === select.id
        );
    }

    function normalise(value) {
        return (value || "")
            .trim()
            .toLocaleLowerCase();
    }

    function optionLabel(option) {
        return (
            option.dataset.originalText ||
            option.textContent ||
            ""
        ).trim();
    }

    function setEnabled(select, enabled) {
        select.disabled = !enabled;

        const search = findSearchInput(select);
        if (search) {
            search.disabled = !enabled;

            if (!enabled) {
                search.value = "";
                closeSuggestions(search);
            }
        }
    }

    function resetSelect(select, placeholder, enabled = false) {
        select.innerHTML = "";

        const option = document.createElement("option");
        option.value = "";
        option.textContent = placeholder;

        select.appendChild(option);
        setEnabled(select, enabled);
    }

    function populateSelect(select, items, placeholder) {
        select.innerHTML = "";

        const first = document.createElement("option");
        first.value = "";
        first.textContent = placeholder;
        select.appendChild(first);

        for (const item of items) {
            const option = document.createElement("option");
            option.value = String(item.id);
            option.textContent = item.text;
            option.dataset.originalText = item.text;
            select.appendChild(option);
        }

        setEnabled(select, true);

        const search = findSearchInput(select);
        if (search) {
            search.value = "";
            closeSuggestions(search);
        }
    }

    function setLoading(select, label) {
        resetSelect(select, label, false);
    }

    async function loadOptions(url, select, placeholder) {
        setLoading(select, "Loading…");

        try {
            const response = await fetch(url, {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const payload = await response.json();

            populateSelect(
                select,
                payload.results || [],
                placeholder
            );
        } catch (error) {
            console.error("Location loading failed:", error);

            resetSelect(
                select,
                "Unable to load locations",
                false
            );
        }
    }

    // ============================================================
    // CASCADING LOCATION LOADERS
    // ============================================================

    province.addEventListener("change", async () => {
        syncSearchFromSelect(province);

        resetSelect(
            district,
            "Select province first",
            false
        );
        resetSelect(
            ds,
            "Select district first",
            false
        );
        resetSelect(
            gn,
            "Select Divisional Secretariat first",
            false
        );

        if (!province.value) return;

        await loadOptions(
            `${districtApi}?province=${encodeURIComponent(province.value)}`,
            district,
            "All districts in selected province"
        );
    });

    district.addEventListener("change", async () => {
        syncSearchFromSelect(district);

        resetSelect(
            ds,
            "Select district first",
            false
        );
        resetSelect(
            gn,
            "Select Divisional Secretariat first",
            false
        );

        if (!district.value) return;

        await loadOptions(
            `${dsApi}?district=${encodeURIComponent(district.value)}`,
            ds,
            "All Divisional Secretariats in selected district"
        );
    });

    ds.addEventListener("change", async () => {
        syncSearchFromSelect(ds);

        resetSelect(
            gn,
            "Select Divisional Secretariat first",
            false
        );

        if (!ds.value) return;

        await loadOptions(
            `${gnApi}?ds=${encodeURIComponent(ds.value)}`,
            gn,
            "All GN Divisions in selected DS"
        );
    });

    gn.addEventListener("change", () => {
        syncSearchFromSelect(gn);
    });

    // ============================================================
    // AUTOCOMPLETE
    // ============================================================

    function ensureSuggestionBox(input) {
        const wrapper = input.closest(".directory-option-search");
        if (!wrapper) return null;

        let box = wrapper.querySelector(
            ".directory-autocomplete-suggestions"
        );

        if (!box) {
            box = document.createElement("div");
            box.className = "directory-autocomplete-suggestions";
            box.setAttribute("role", "listbox");
            box.hidden = true;

            wrapper.appendChild(box);
        }

        return box;
    }

    function closeSuggestions(input) {
        const wrapper = input.closest(".directory-option-search");
        if (!wrapper) return;

        const box = wrapper.querySelector(
            ".directory-autocomplete-suggestions"
        );

        if (box) {
            box.hidden = true;
            box.innerHTML = "";
        }

        input.removeAttribute("aria-activedescendant");
        input.setAttribute("aria-expanded", "false");
        input.dataset.activeSuggestion = "-1";
    }

    function getMatchingOptions(select, term) {
        const normalisedTerm = normalise(term);

        if (normalisedTerm.length < MIN_AUTOCOMPLETE_CHARS) {
            return [];
        }

        return Array.from(select.options)
            .filter((option) => {
                if (!option.value) return false;

                return normalise(
                    optionLabel(option)
                ).includes(normalisedTerm);
            })
            .slice(0, MAX_SUGGESTIONS);
    }

    function highlightMatch(label, term) {
        const safeLabel = document.createElement("span");
        safeLabel.textContent = label;

        const normalisedLabel = normalise(label);
        const normalisedTerm = normalise(term);
        const index = normalisedLabel.indexOf(normalisedTerm);

        if (index < 0) {
            return safeLabel;
        }

        const fragment = document.createDocumentFragment();

        const before = document.createTextNode(
            label.slice(0, index)
        );

        const match = document.createElement("strong");
        match.textContent = label.slice(
            index,
            index + term.length
        );

        const after = document.createTextNode(
            label.slice(index + term.length)
        );

        fragment.append(before, match, after);

        return fragment;
    }

    function renderSuggestions(input, select) {
        const box = ensureSuggestionBox(input);
        if (!box) return;

        const term = input.value.trim();

        if (
            input.disabled ||
            term.length < MIN_AUTOCOMPLETE_CHARS
        ) {
            closeSuggestions(input);
            return;
        }

        const matches = getMatchingOptions(select, term);

        box.innerHTML = "";

        if (!matches.length) {
            const empty = document.createElement("div");
            empty.className = "directory-autocomplete-empty";
            empty.textContent = "No matching locations found";

            box.appendChild(empty);
            box.hidden = false;

            input.setAttribute("aria-expanded", "true");
            input.dataset.activeSuggestion = "-1";
            return;
        }

        matches.forEach((option, index) => {
            const item = document.createElement("button");

            item.type = "button";
            item.className = "directory-autocomplete-item";
            item.id = `${input.id || select.id}-suggestion-${index}`;
            item.dataset.value = option.value;
            item.dataset.index = String(index);
            item.setAttribute("role", "option");
            item.setAttribute("aria-selected", "false");

            const icon = document.createElement("span");
            icon.className = "directory-autocomplete-icon";
            icon.innerHTML = '<i class="bi bi-geo-alt"></i>';

            const text = document.createElement("span");
            text.className = "directory-autocomplete-text";
            text.appendChild(
                highlightMatch(
                    optionLabel(option),
                    term
                )
            );

            item.append(icon, text);

            item.addEventListener("mousedown", (event) => {
                // Prevent input blur before the suggestion can be selected.
                event.preventDefault();
            });

            item.addEventListener("click", () => {
                chooseSuggestion(
                    input,
                    select,
                    option.value,
                    optionLabel(option)
                );
            });

            box.appendChild(item);
        });

        box.hidden = false;
        input.setAttribute("aria-expanded", "true");
        input.dataset.activeSuggestion = "-1";
    }

    function chooseSuggestion(
        input,
        select,
        value,
        label
    ) {
        select.value = value;
        input.value = label;

        closeSuggestions(input);

        // This also triggers the next cascade level.
        select.dispatchEvent(
            new Event("change", { bubbles: true })
        );
    }

    function getSuggestionItems(input) {
        const wrapper = input.closest(".directory-option-search");
        if (!wrapper) return [];

        return Array.from(
            wrapper.querySelectorAll(
                ".directory-autocomplete-item"
            )
        );
    }

    function setActiveSuggestion(input, newIndex) {
        const items = getSuggestionItems(input);
        if (!items.length) return;

        const safeIndex = (
            newIndex + items.length
        ) % items.length;

        items.forEach((item, index) => {
            const active = index === safeIndex;

            item.classList.toggle(
                "is-active",
                active
            );

            item.setAttribute(
                "aria-selected",
                active ? "true" : "false"
            );
        });

        input.dataset.activeSuggestion = String(safeIndex);

        const activeItem = items[safeIndex];

        input.setAttribute(
            "aria-activedescendant",
            activeItem.id
        );

        activeItem.scrollIntoView({
            block: "nearest",
        });
    }

    function syncSearchFromSelect(select) {
        const input = findSearchInput(select);
        if (!input) return;

        if (!select.value) {
            input.value = "";
            closeSuggestions(input);
            return;
        }

        const selected = select.selectedOptions[0];

        if (selected) {
            input.value = optionLabel(selected);
        }

        closeSuggestions(input);
    }

    for (const input of searchInputs) {
        const target = document.getElementById(
            input.dataset.optionSearch
        );

        if (!target) continue;

        input.setAttribute("autocomplete", "off");
        input.setAttribute("aria-autocomplete", "list");
        input.setAttribute("aria-expanded", "false");

        ensureSuggestionBox(input);

        input.addEventListener("input", () => {
            renderSuggestions(input, target);
        });

        input.addEventListener("focus", () => {
            if (
                input.value.trim().length >=
                MIN_AUTOCOMPLETE_CHARS
            ) {
                renderSuggestions(input, target);
            }
        });

        input.addEventListener("keydown", (event) => {
            const items = getSuggestionItems(input);

            if (event.key === "Escape") {
                closeSuggestions(input);
                return;
            }

            if (
                event.key !== "ArrowDown" &&
                event.key !== "ArrowUp" &&
                event.key !== "Enter"
            ) {
                return;
            }

            if (!items.length) {
                if (event.key !== "Enter") {
                    renderSuggestions(input, target);
                }
                return;
            }

            let activeIndex = Number(
                input.dataset.activeSuggestion || "-1"
            );

            if (event.key === "ArrowDown") {
                event.preventDefault();
                setActiveSuggestion(
                    input,
                    activeIndex + 1
                );
                return;
            }

            if (event.key === "ArrowUp") {
                event.preventDefault();
                setActiveSuggestion(
                    input,
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

                const activeItem = items[activeIndex];

                if (activeItem) {
                    const selectedOption = Array.from(
                        target.options
                    ).find(
                        (option) =>
                            option.value ===
                            activeItem.dataset.value
                    );

                    if (selectedOption) {
                        chooseSuggestion(
                            input,
                            target,
                            selectedOption.value,
                            optionLabel(selectedOption)
                        );
                    }
                }
            }
        });
    }

    document.addEventListener("mousedown", (event) => {
        for (const input of searchInputs) {
            const wrapper = input.closest(
                ".directory-option-search"
            );

            if (
                wrapper &&
                !wrapper.contains(event.target)
            ) {
                closeSuggestions(input);
            }
        }
    });
})();
