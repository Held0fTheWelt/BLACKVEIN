/**
 * Slogan management: list, create, edit, delete, activate/deactivate. Uses backend API with JWT.
 * Initializes on DOMContentLoaded; requires ManageAuth (loaded before this script in extra_scripts).
 */
(function() {
    var apiRef = null;
    function $(id) { return id ? document.getElementById(id) : null; }

    function getFilters() {
        var placement = ($("slogan-filter-placement") && $("slogan-filter-placement").value) || "";
        var lang = ($("slogan-filter-lang") && $("slogan-filter-lang").value) || "";
        return { placement: placement || undefined, language_code: lang || undefined };
    }

    function showLoading(show) {
        var el = $("slogan-loading");
        var tbody = $("slogan-tbody");
        var err = $("slogan-error");
        if (el) el.style.display = show ? "block" : "none";
        if (tbody) tbody.innerHTML = show ? "" : (tbody.innerHTML || "");
        if (err) { err.hidden = true; }
    }

    function showError(msg) {
        showLoading(false);
        var err = $("slogan-error");
        if (err) { err.textContent = msg || "Error"; err.hidden = false; }
    }

    function escapeHtml(s) {
        if (s == null) return "";
        var div = document.createElement("div");
        div.textContent = s;
        return div.innerHTML;
    }

    function truncate(s, len) {
        if (s == null) return "";
        s = String(s);
        return s.length <= len ? s : s.slice(0, len) + "\u2026";
    }

    function fetchList() {
        if (!apiRef) return;
        showLoading(true);
        var f = getFilters();
        var qs = [];
        if (f.placement) qs.push("placement_key=" + encodeURIComponent(f.placement));
        if (f.language_code) qs.push("language_code=" + encodeURIComponent(f.language_code));
        var url = "/api/v1/slogans" + (qs.length ? "?" + qs.join("&") : "");
        apiRef(url)
            .then(function(data) {
                showLoading(false);
                var items = (data && data.items) || [];
                var tbody = $("slogan-tbody");
                if (!tbody) return;
                tbody.innerHTML = "";
                items.forEach(function(s) {
                    var tr = document.createElement("tr");
                    tr.innerHTML =
                        "<td title=\"" + escapeHtml(s.text) + "\">" + escapeHtml(truncate(s.text, 50)) + "</td>" +
                        "<td>" + escapeHtml(s.placement_key) + "</td>" +
                        "<td>" + escapeHtml(s.language_code) + "</td>" +
                        "<td>" + (s.is_active ? "Yes" : "No") + "</td>" +
                        "<td>" + (s.is_pinned ? "Yes" : "No") + "</td>" +
                        "<td>" + escapeHtml(String(s.priority)) + "</td>" +
                        "<td>" +
                        "<button type=\"button\" class=\"btn btn-ghost btn-sm slogan-edit\" data-id=\"" + s.id + "\">Edit</button> " +
                        (s.is_active
                            ? "<button type=\"button\" class=\"btn btn-ghost btn-sm slogan-deactivate\" data-id=\"" + s.id + "\">Deactivate</button> "
                            : "<button type=\"button\" class=\"btn btn-ghost btn-sm slogan-activate\" data-id=\"" + s.id + "\">Activate</button> ") +
                        "<button type=\"button\" class=\"btn btn-ghost btn-sm slogan-delete\" data-id=\"" + s.id + "\">Delete</button>" +
                        "</td>";
                    tbody.appendChild(tr);
                });
            })
            .catch(function(e) {
                showError(e && e.message ? e.message : "Failed to load slogans.");
            });
    }

    function showForm(editId) {
        var wrap = $("slogan-form-wrap");
        var title = $("slogan-form-title");
        if (wrap) wrap.hidden = false;
        if (title) title.textContent = editId ? "Edit slogan" : "New slogan";
        $("slogan-id").value = editId || "";
        if (!editId) {
            $("slogan-text").value = "";
            $("slogan-category").value = "landing_teaser";
            $("slogan-placement").value = "landing.teaser.primary";
            $("slogan-lang").value = "de";
            $("slogan-active").checked = true;
            $("slogan-pinned").checked = false;
            $("slogan-priority").value = "0";
            return;
        }
        apiRef("/api/v1/slogans/" + editId)
            .then(function(s) {
                $("slogan-text").value = s.text || "";
                $("slogan-category").value = s.category || "landing_teaser";
                $("slogan-placement").value = s.placement_key || "landing.teaser.primary";
                $("slogan-lang").value = s.language_code || "de";
                $("slogan-active").checked = !!s.is_active;
                $("slogan-pinned").checked = !!s.is_pinned;
                $("slogan-priority").value = String(s.priority != null ? s.priority : 0);
            })
            .catch(function(e) {
                showError(e && e.message ? e.message : "Failed to load slogan.");
            });
    }

    function hideForm() {
        var wrap = $("slogan-form-wrap");
        if (wrap) wrap.hidden = true;
    }

    function saveSlogan(e) {
        e.preventDefault();
        var id = ($("slogan-id").value || "").trim();
        var payload = {
            text: ($("slogan-text").value || "").trim(),
            category: $("slogan-category").value,
            placement_key: $("slogan-placement").value,
            language_code: $("slogan-lang").value,
            is_active: $("slogan-active").checked,
            is_pinned: $("slogan-pinned").checked,
            priority: parseInt($("slogan-priority").value, 10) || 0,
        };
        if (!payload.text) {
            showError("Text is required.");
            return;
        }
        var method = id ? "PUT" : "POST";
        var url = id ? "/api/v1/slogans/" + id : "/api/v1/slogans";
        apiRef(url, { method: method, body: JSON.stringify(payload) })
            .then(function() {
                hideForm();
                fetchList();
            })
            .catch(function(err) {
                showError(err && err.message ? err.message : "Save failed.");
            });
    }

    function deleteSlogan(id) {
        if (!confirm("Delete this slogan?")) return;
        apiRef("/api/v1/slogans/" + id, { method: "DELETE" })
            .then(function() { fetchList(); })
            .catch(function(e) { showError(e && e.message ? e.message : "Delete failed."); });
    }

    function activateSlogan(id) {
        apiRef("/api/v1/slogans/" + id + "/activate", { method: "POST" })
            .then(function() { fetchList(); })
            .catch(function(e) { showError(e && e.message ? e.message : "Activate failed."); });
    }

    function deactivateSlogan(id) {
        apiRef("/api/v1/slogans/" + id + "/deactivate", { method: "POST" })
            .then(function() { fetchList(); })
            .catch(function(e) { showError(e && e.message ? e.message : "Deactivate failed."); });
    }

    function initSlogansPage() {
        var api = window.ManageAuth && window.ManageAuth.apiFetchWithAuth;
        if (!api) {
            console.error("[manage_slogans] ManageAuth.apiFetchWithAuth not available.");
            var errEl = $("slogan-error");
            if (errEl) { errEl.textContent = "Auth not loaded. Refresh the page."; errEl.hidden = false; }
            return;
        }
        apiRef = api;

        fetchList();
        if ($("slogan-filter-placement")) $("slogan-filter-placement").addEventListener("change", fetchList);
        if ($("slogan-filter-lang")) $("slogan-filter-lang").addEventListener("change", fetchList);
        if ($("slogan-new")) $("slogan-new").addEventListener("click", function() { showForm(null); });
        if ($("slogan-form-cancel")) $("slogan-form-cancel").addEventListener("click", hideForm);
        if ($("slogan-form")) $("slogan-form").addEventListener("submit", saveSlogan);
        var tbody = $("slogan-tbody");
        if (tbody) tbody.addEventListener("click", function(e) {
            var t = e.target;
            if (!t || !t.classList) return;
            var id = t.getAttribute("data-id");
            if (!id) return;
            if (t.classList.contains("slogan-edit")) showForm(id);
            else if (t.classList.contains("slogan-delete")) deleteSlogan(id);
            else if (t.classList.contains("slogan-activate")) activateSlogan(id);
            else if (t.classList.contains("slogan-deactivate")) deactivateSlogan(id);
        });
    }

    function run() {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", initSlogansPage);
        } else {
            initSlogansPage();
        }
    }
    run();
})();
