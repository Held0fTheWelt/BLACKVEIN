/**
 * Area management: list, create, edit, delete. Admin only (backend enforces).
 */
(function() {
    var apiRef = null;

    function $(id) { return document.getElementById(id); }

    function showLoading(show) {
        var loading = $("manage-areas-loading");
        var wrap = $("manage-areas-table-wrap");
        var err = $("manage-areas-error");
        if (loading) loading.hidden = !show;
        if (wrap) wrap.hidden = true;
        if (err) err.hidden = true;
    }

    function showError(msg) {
        showLoading(false);
        var wrap = $("manage-areas-table-wrap");
        var err = $("manage-areas-error");
        if (wrap) wrap.hidden = true;
        if (err) { err.textContent = msg || "Failed to load."; err.hidden = false; }
    }

    function renderList(items) {
        showLoading(false);
        var err = $("manage-areas-error");
        var wrap = $("manage-areas-table-wrap");
        var tbody = $("manage-areas-tbody");
        if (err) err.hidden = true;
        if (!items || items.length === 0) {
            if (wrap) wrap.hidden = true;
            return;
        }
        if (wrap) wrap.hidden = false;
        if (tbody) {
            tbody.innerHTML = "";
            items.forEach(function(a) {
                var tr = document.createElement("tr");
                tr.dataset.id = a.id;
                var sys = a.is_system ? "Yes" : "—";
                tr.innerHTML =
                    "<td>" + (a.id || "") + "</td>" +
                    "<td>" + (a.slug || "").replace(/</g, "&lt;") + "</td>" +
                    "<td>" + (a.name || "").replace(/</g, "&lt;") + "</td>" +
                    "<td>" + sys + "</td>";
                tr.addEventListener("click", function() { selectArea(a.id); });
                tbody.appendChild(tr);
            });
        }
    }

    function fetchList() {
        if (!apiRef) return;
        showLoading(true);
        apiRef("/api/v1/areas?limit=100")
            .then(function(data) {
                var items = data.items || [];
                renderList(items);
            })
            .catch(function(e) {
                showError(e.message || "Failed to load areas. (Admin only)");
            });
    }

    function selectArea(id) {
        var form = $("manage-areas-form");
        var empty = $("manage-areas-editor-empty");
        if (!id) {
            if (form) form.hidden = true;
            if (empty) empty.hidden = false;
            return;
        }
        if (empty) empty.hidden = true;
        if (form) form.hidden = false;
        apiRef("/api/v1/areas/" + id)
            .then(function(area) {
                ($("manage-areas-id") || {}).value = area.id;
                ($("manage-areas-name") || {}).value = area.name || "";
                ($("manage-areas-slug") || {}).value = area.slug || "";
                ($("manage-areas-description") || {}).value = area.description || "";
                ($("manage-areas-editor-title") || {}).textContent = "Edit area";
                var slugEl = $("manage-areas-slug");
                var delBtn = $("manage-areas-delete-btn");
                if (slugEl) slugEl.readOnly = !!area.is_system;
                if (delBtn) delBtn.hidden = !!area.is_system;
            })
            .catch(function(e) {
                if ($("manage-areas-form-error")) {
                    $("manage-areas-form-error").textContent = e.message || "Failed to load area.";
                    $("manage-areas-form-error").hidden = false;
                }
            });
    }

    function showFormError(msg) {
        var el = $("manage-areas-form-error");
        var ok = $("manage-areas-form-success");
        if (ok) ok.hidden = true;
        if (el) { el.textContent = msg || "Error."; el.hidden = false; }
    }

    function showFormSuccess(msg) {
        var el = $("manage-areas-form-success");
        var err = $("manage-areas-form-error");
        if (err) err.hidden = true;
        if (el) { el.textContent = msg || "Saved."; el.hidden = false; setTimeout(function() { el.hidden = true; }, 3000); }
    }

    function onSave(e) {
        e.preventDefault();
        var id = ($("manage-areas-id") || {}).value;
        var name = ($("manage-areas-name") || {}).value.trim();
        if (!name) {
            showFormError("Name is required.");
            return;
        }
        var slug = ($("manage-areas-slug") || {}).value.trim().toLowerCase().replace(/\s+/g, "_");
        var description = ($("manage-areas-description") || {}).value.trim() || null;
        var saveBtn = $("manage-areas-save");
        if (saveBtn) saveBtn.disabled = true;
        var payload = { name: name };
        if (slug) payload.slug = slug;
        if (description !== null) payload.description = description;
        var method = id ? "PUT" : "POST";
        var url = id ? "/api/v1/areas/" + id : "/api/v1/areas";
        apiRef(url, { method: method, body: JSON.stringify(payload) })
            .then(function(area) {
                showFormSuccess("Saved.");
                if (saveBtn) saveBtn.disabled = false;
                fetchList();
                selectArea(area.id);
            })
            .catch(function(e) {
                showFormError(e.message || "Save failed.");
                if (saveBtn) saveBtn.disabled = false;
            });
    }

    function onNew() {
        ($("manage-areas-id") || {}).value = "";
        ($("manage-areas-name") || {}).value = "";
        ($("manage-areas-slug") || {}).value = "";
        ($("manage-areas-description") || {}).value = "";
        var slugEl = $("manage-areas-slug");
        if (slugEl) slugEl.readOnly = false;
        $("manage-areas-form").hidden = false;
        $("manage-areas-editor-empty").hidden = true;
        $("manage-areas-editor-title").textContent = "New area";
        $("manage-areas-delete-btn").hidden = true;
        if ($("manage-areas-form-error")) $("manage-areas-form-error").hidden = true;
    }

    function onDelete() {
        var id = ($("manage-areas-id") || {}).value;
        if (!id) return;
        if (!confirm("Delete this area? Fails if assigned to users or features.")) return;
        apiRef("/api/v1/areas/" + id, { method: "DELETE" })
            .then(function() {
                ($("manage-areas-id") || {}).value = "";
                $("manage-areas-form").hidden = true;
                $("manage-areas-editor-empty").hidden = false;
                fetchList();
            })
            .catch(function(e) {
                showFormError(e.message || "Delete failed.");
            });
    }

    function init() {
        var api = window.ManageAuth && window.ManageAuth.apiFetchWithAuth;
        if (!api) {
            var errEl = $("manage-areas-error");
            if (errEl) { errEl.textContent = "Auth not loaded. Refresh the page."; errEl.hidden = false; }
            return;
        }
        apiRef = api;
        var form = $("manage-areas-form");
        var saveBtn = $("manage-areas-save");
        var delBtn = $("manage-areas-delete-btn");
        var newBtn = $("manage-areas-new-btn");
        if (form) form.addEventListener("submit", onSave);
        if (delBtn) delBtn.addEventListener("click", onDelete);
        if (newBtn) newBtn.addEventListener("click", onNew);
        fetchList();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
