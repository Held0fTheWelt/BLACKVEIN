/**
 * Role management: list, create, edit, delete. Admin only (backend enforces).
 */
(function() {
    var apiRef = null;

    function $(id) { return document.getElementById(id); }

    function showLoading(show) {
        var loading = $("manage-roles-loading");
        var wrap = $("manage-roles-table-wrap");
        var err = $("manage-roles-error");
        if (loading) loading.hidden = !show;
        if (wrap) wrap.hidden = true;
        if (err) err.hidden = true;
    }

    function showError(msg) {
        showLoading(false);
        var wrap = $("manage-roles-table-wrap");
        var err = $("manage-roles-error");
        if (wrap) wrap.hidden = true;
        if (err) { err.textContent = msg || "Failed to load."; err.hidden = false; }
    }

    function renderList(items) {
        showLoading(false);
        var err = $("manage-roles-error");
        var wrap = $("manage-roles-table-wrap");
        var tbody = $("manage-roles-tbody");
        if (err) err.hidden = true;
        if (!items || items.length === 0) {
            if (wrap) wrap.hidden = true;
            return;
        }
        if (wrap) wrap.hidden = false;
        if (tbody) {
            tbody.innerHTML = "";
            items.forEach(function(r) {
                var tr = document.createElement("tr");
                tr.dataset.id = r.id;
                var level = r.default_role_level != null ? r.default_role_level : "—";
                var desc = (r.description || "").replace(/</g, "&lt;").slice(0, 40);
                if ((r.description || "").length > 40) desc += "…";
                tr.innerHTML =
                    "<td>" + (r.id || "") + "</td>" +
                    "<td>" + (r.name || "").replace(/</g, "&lt;") + "</td>" +
                    "<td>" + level + "</td>" +
                    "<td>" + (desc || "—") + "</td>";
                tr.addEventListener("click", function() { selectRole(r.id); });
                tbody.appendChild(tr);
            });
        }
    }

    function fetchList() {
        if (!apiRef) return;
        showLoading(true);
        apiRef("/api/v1/roles?limit=100")
            .then(function(data) {
                var items = data.items || [];
                renderList(items);
            })
            .catch(function(e) {
                showError(e.message || "Failed to load roles. (Admin only)");
            });
    }

    function selectRole(id) {
        var form = $("manage-roles-form");
        var empty = $("manage-roles-editor-empty");
        if (!id) {
            if (form) form.hidden = true;
            if (empty) empty.hidden = false;
            return;
        }
        if (empty) empty.hidden = true;
        if (form) form.hidden = false;
        apiRef("/api/v1/roles/" + id)
            .then(function(role) {
                ($("manage-roles-id") || {}).value = role.id;
                ($("manage-roles-name") || {}).value = role.name || "";
                ($("manage-roles-description") || {}).value = role.description || "";
                ($("manage-roles-default-level") || {}).value = (role.default_role_level != null && role.default_role_level !== "") ? role.default_role_level : "";
                ($("manage-roles-editor-title") || {}).textContent = "Edit role";
                $("manage-roles-delete-btn").hidden = false;
            })
            .catch(function(e) {
                if ($("manage-roles-form-error")) {
                    $("manage-roles-form-error").textContent = e.message || "Failed to load role.";
                    $("manage-roles-form-error").hidden = false;
                }
            });
    }

    function showFormError(msg) {
        var el = $("manage-roles-form-error");
        var ok = $("manage-roles-form-success");
        if (ok) ok.hidden = true;
        if (el) { el.textContent = msg || "Error."; el.hidden = false; }
    }

    function showFormSuccess(msg) {
        var el = $("manage-roles-form-success");
        var err = $("manage-roles-form-error");
        if (err) err.hidden = true;
        if (el) { el.textContent = msg || "Saved."; el.hidden = false; setTimeout(function() { el.hidden = true; }, 3000); }
    }

    function onSave(e) {
        e.preventDefault();
        var id = ($("manage-roles-id") || {}).value;
        var name = ($("manage-roles-name") || {}).value.trim().toLowerCase();
        if (!name) {
            showFormError("Name is required.");
            return;
        }
        var description = ($("manage-roles-description") || {}).value.trim() || null;
        var defaultLevelEl = $("manage-roles-default-level");
        var defaultLevel = defaultLevelEl && defaultLevelEl.value !== "" ? parseInt(defaultLevelEl.value, 10) : null;
        if (defaultLevel !== null && isNaN(defaultLevel)) defaultLevel = null;
        var saveBtn = $("manage-roles-save");
        if (saveBtn) saveBtn.disabled = true;
        var payload = { name: name };
        if (description !== null) payload.description = description;
        if (defaultLevel !== null) payload.default_role_level = defaultLevel;
        var method = id ? "PUT" : "POST";
        var url = id ? "/api/v1/roles/" + id : "/api/v1/roles";
        apiRef(url, { method: method, body: JSON.stringify(payload) })
            .then(function(role) {
                showFormSuccess("Saved.");
                if (saveBtn) saveBtn.disabled = false;
                fetchList();
                selectRole(role.id);
            })
            .catch(function(e) {
                showFormError(e.message || "Save failed.");
                if (saveBtn) saveBtn.disabled = false;
            });
    }

    function onNew() {
        ($("manage-roles-id") || {}).value = "";
        ($("manage-roles-name") || {}).value = "";
        ($("manage-roles-description") || {}).value = "";
        ($("manage-roles-default-level") || {}).value = "";
        $("manage-roles-form").hidden = false;
        $("manage-roles-editor-empty").hidden = true;
        $("manage-roles-editor-title").textContent = "New role";
        $("manage-roles-delete-btn").hidden = true;
        if ($("manage-roles-form-error")) $("manage-roles-form-error").hidden = true;
    }

    function onDelete() {
        var id = ($("manage-roles-id") || {}).value;
        if (!id) return;
        if (!confirm("Delete this role? Fails if any user has this role.")) return;
        apiRef("/api/v1/roles/" + id, { method: "DELETE" })
            .then(function() {
                ($("manage-roles-id") || {}).value = "";
                $("manage-roles-form").hidden = true;
                $("manage-roles-editor-empty").hidden = false;
                fetchList();
            })
            .catch(function(e) {
                showFormError(e.message || "Delete failed.");
            });
    }

    function init() {
        var api = window.ManageAuth && window.ManageAuth.apiFetchWithAuth;
        if (!api) {
            var errEl = $("manage-roles-error");
            if (errEl) { errEl.textContent = "Auth not loaded. Refresh the page."; errEl.hidden = false; }
            return;
        }
        apiRef = api;
        var form = $("manage-roles-form");
        var saveBtn = $("manage-roles-save");
        var delBtn = $("manage-roles-delete-btn");
        var newBtn = $("manage-roles-new-btn");
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
