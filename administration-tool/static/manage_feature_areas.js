/**
 * Feature-to-area access mapping: list features, assign areas per feature. Admin only.
 */
(function() {
    var apiRef = null;
    var allAreas = [];

    function $(id) { return document.getElementById(id); }

    function showLoading(show) {
        var loading = $("manage-feature-areas-loading");
        var wrap = $("manage-feature-areas-table-wrap");
        var err = $("manage-feature-areas-error");
        if (loading) loading.hidden = !show;
        if (wrap) wrap.hidden = true;
        if (err) err.hidden = true;
    }

    function showError(msg) {
        showLoading(false);
        var wrap = $("manage-feature-areas-table-wrap");
        var err = $("manage-feature-areas-error");
        if (wrap) wrap.hidden = true;
        if (err) { err.textContent = msg || "Failed to load."; err.hidden = false; }
    }

    function loadAreas() {
        return apiRef("/api/v1/areas?limit=100").then(function(data) {
            allAreas = data.items || [];
            return allAreas;
        });
    }

    function renderList(items) {
        showLoading(false);
        var err = $("manage-feature-areas-error");
        var wrap = $("manage-feature-areas-table-wrap");
        var tbody = $("manage-feature-areas-tbody");
        if (err) err.hidden = true;
        if (!items || items.length === 0) {
            if (wrap) wrap.hidden = true;
            return;
        }
        if (wrap) wrap.hidden = false;
        if (tbody) {
            tbody.innerHTML = "";
            items.forEach(function(m) {
                var tr = document.createElement("tr");
                tr.dataset.featureId = m.feature_id;
                var areaText = (m.area_slugs && m.area_slugs.length) ? m.area_slugs.join(", ") : "(all)";
                tr.innerHTML =
                    "<td>" + (m.feature_id || "").replace(/</g, "&lt;") + "</td>" +
                    "<td>" + areaText.replace(/</g, "&lt;") + "</td>";
                tr.addEventListener("click", function() { selectFeature(m.feature_id); });
                tbody.appendChild(tr);
            });
        }
    }

    function fetchList() {
        if (!apiRef) return;
        showLoading(true);
        apiRef("/api/v1/feature-areas")
            .then(function(data) {
                var items = data.items || [];
                renderList(items);
            })
            .catch(function(e) {
                showError(e.message || "Failed to load feature areas. (Admin only)");
            });
    }

    function fillAreaMultiSelect(selectedIds) {
        var sel = $("manage-feature-areas-multi");
        if (!sel) return;
        sel.innerHTML = "";
        var set = (selectedIds || []).reduce(function(s, id) { s[id] = true; return s; }, {});
        allAreas.forEach(function(a) {
            var opt = document.createElement("option");
            opt.value = a.id;
            opt.textContent = (a.slug || a.name || a.id);
            if (set[a.id]) opt.selected = true;
            sel.appendChild(opt);
        });
    }

    function selectFeature(featureId) {
        var form = $("manage-feature-areas-form");
        var empty = $("manage-feature-areas-editor-empty");
        if (!featureId) {
            if (form) form.hidden = true;
            if (empty) empty.hidden = false;
            return;
        }
        if (empty) empty.hidden = true;
        if (form) form.hidden = false;
        ($("manage-feature-areas-feature-id") || {}).value = featureId;
        ($("manage-feature-areas-feature-label") || {}).textContent = "Feature: " + featureId;
        apiRef("/api/v1/feature-areas/" + encodeURIComponent(featureId))
            .then(function(m) {
                fillAreaMultiSelect(m.area_ids || []);
            })
            .catch(function(e) {
                fillAreaMultiSelect([]);
                if ($("manage-feature-areas-form-error")) {
                    $("manage-feature-areas-form-error").textContent = e.message || "Failed to load.";
                    $("manage-feature-areas-form-error").hidden = false;
                }
            });
    }

    function showFormError(msg) {
        var el = $("manage-feature-areas-form-error");
        var ok = $("manage-feature-areas-form-success");
        if (ok) ok.hidden = true;
        if (el) { el.textContent = msg || "Error."; el.hidden = false; }
    }

    function showFormSuccess(msg) {
        var el = $("manage-feature-areas-form-success");
        var err = $("manage-feature-areas-form-error");
        if (err) err.hidden = true;
        if (el) { el.textContent = msg || "Saved."; el.hidden = false; setTimeout(function() { el.hidden = true; }, 3000); }
    }

    function onSave(e) {
        e.preventDefault();
        var featureId = ($("manage-feature-areas-feature-id") || {}).value;
        if (!featureId) return;
        var sel = $("manage-feature-areas-multi");
        var areaIds = [];
        if (sel) {
            for (var i = 0; i < sel.options.length; i++) {
                if (sel.options[i].selected) areaIds.push(parseInt(sel.options[i].value, 10));
            }
        }
        var saveBtn = $("manage-feature-areas-save");
        if (saveBtn) saveBtn.disabled = true;
        apiRef("/api/v1/feature-areas/" + encodeURIComponent(featureId), {
            method: "PUT",
            body: JSON.stringify({ area_ids: areaIds })
        })
            .then(function() {
                showFormSuccess("Saved.");
                if (saveBtn) saveBtn.disabled = false;
                fetchList();
            })
            .catch(function(e) {
                showFormError(e.message || "Save failed.");
                if (saveBtn) saveBtn.disabled = false;
            });
    }

    function init() {
        var api = window.ManageAuth && window.ManageAuth.apiFetchWithAuth;
        if (!api) {
            var errEl = $("manage-feature-areas-error");
            if (errEl) { errEl.textContent = "Auth not loaded. Refresh the page."; errEl.hidden = false; }
            return;
        }
        apiRef = api;
        var form = $("manage-feature-areas-form");
        var saveBtn = $("manage-feature-areas-save");
        if (form) form.addEventListener("submit", onSave);
        showLoading(true);
        loadAreas()
            .then(function() {
                fetchList();
            })
            .catch(function(e) {
                showError(e.message || "Failed to load areas.");
            });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
