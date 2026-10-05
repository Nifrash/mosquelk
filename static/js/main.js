document.addEventListener("DOMContentLoaded", function () {
    console.log("Sri Lanka Mosque Platform loaded successfully.");

    const form = document.querySelector("[data-mosque-location-form]");
    if (!form) return;

    const province = form.querySelector("[data-location-province]");
    const district = form.querySelector("[data-location-district]");
    const ds = form.querySelector("[data-location-ds]");
    const gn = form.querySelector("[data-location-gn]");

    const districtUrl = form.dataset.districtUrl;
    const dsUrl = form.dataset.dsUrl;
    const gnUrl = form.dataset.gnUrl;

    function resetSelect(select, placeholder) {
        if (!select) return;
        select.innerHTML = "";
        const option = document.createElement("option");
        option.value = "";
        option.textContent = placeholder;
        select.appendChild(option);
    }

    async function loadOptions(url, param, value, select, placeholder) {
        resetSelect(select, placeholder);
        if (!value || !select) return;

        select.disabled = true;
        try {
            const response = await fetch(`${url}?${encodeURIComponent(param)}=${encodeURIComponent(value)}`, {
                headers: {"X-Requested-With": "XMLHttpRequest"}
            });
            if (!response.ok) throw new Error("Location lookup failed");
            const data = await response.json();
            data.results.forEach(item => {
                const option = document.createElement("option");
                option.value = item.id;
                option.textContent = item.text;
                select.appendChild(option);
            });
        } catch (error) {
            console.error(error);
        } finally {
            select.disabled = false;
        }
    }

    if (province) {
        province.addEventListener("change", async function () {
            resetSelect(ds, "---------");
            resetSelect(gn, "---------");
            await loadOptions(districtUrl, "province", province.value, district, "---------");
        });
    }

    if (district) {
        district.addEventListener("change", async function () {
            resetSelect(gn, "---------");
            await loadOptions(dsUrl, "district", district.value, ds, "---------");
        });
    }

    if (ds) {
        ds.addEventListener("change", async function () {
            await loadOptions(gnUrl, "ds", ds.value, gn, "---------");
        });
    }
});
