(function() {
    function $(id) { return id ? document.getElementById(id) : null; }

    function formatDate(iso) {
        if (!iso) return "";
        var d = new Date(iso);
        return isNaN(d.getTime()) ? "" : d.toLocaleString();
    }

    function api() {
        return window.ManageAuth && window.ManageAuth.apiFetchWithAuth;
    }

    // --- Categories ---
    function loadCategories() {
        var apiRef = api();
        if (!apiRef) return;
        var loading = $("manage-forum-categories-loading");
        var errorEl = $("manage-forum-categories-error");
        var empty = $("manage-forum-categories-empty");
        var wrap = $("manage-forum-categories-table-wrap");
        var tbody = $("manage-forum-categories-tbody");
        var count = $("manage-forum-categories-count");
        var footer = $("manage-forum-categories-footer");

        if (loading) loading.hidden = false;
        if (errorEl) { errorEl.hidden = true; errorEl.textContent = ""; }
        if (empty) empty.hidden = true;
        if (wrap) wrap.hidden = true;
        if (footer) footer.hidden = true;

        apiRef("/api/v1/forum/categories")
            .then(function(data) {
                var items = (data && data.items) || [];
                if (loading) loading.hidden = true;
                if (!items.length) {
                    if (empty) empty.hidden = false;
                    return;
                }
                if (tbody) {
                    tbody.innerHTML = "";
                    items.forEach(function(cat) {
                        var tr = document.createElement("tr");
                        tr.dataset.id = cat.id;
                        tr.innerHTML =
                            "<td>" + (cat.title || "") + "</td>" +
                            "<td>" + (cat.slug || "") + "</td>" +
                            "<td>" + (cat.sort_order != null ? String(cat.sort_order) : "") + "</td>" +
                            "<td>" + (cat.is_active ? "Yes" : "No") + "</td>" +
                            "<td>" + (cat.is_private ? "Yes" : "No") + "</td>" +
                            "<td>" + (cat.required_role || "") + "</td>";
                        tr.addEventListener("click", function() { selectCategory(cat); });
                        tbody.appendChild(tr);
                    });
                }
                if (wrap) wrap.hidden = false;
                if (count) count.textContent = items.length + " categories";
                if (footer) footer.hidden = false;
            })
            .catch(function(err) {
                if (loading) loading.hidden = true;
                if (errorEl) {
                    errorEl.textContent = (err && err.message) || "Failed to load categories.";
                    errorEl.hidden = false;
                }
            });
    }

    function selectCategory(cat) {
        var idEl = $("manage-forum-category-id");
        var titleEl = $("manage-forum-category-title");
        var slugEl = $("manage-forum-category-slug");
        var descEl = $("manage-forum-category-description");
        var sortEl = $("manage-forum-category-sort");
        var activeEl = $("manage-forum-category-active");
        var privateEl = $("manage-forum-category-private");
        var roleEl = $("manage-forum-category-required-role");
        var form = $("manage-forum-category-form");
        var empty = $("manage-forum-category-editor-empty");
        var editorTitle = $("manage-forum-category-editor-title");

        if (idEl) idEl.value = cat.id;
        if (titleEl) titleEl.value = cat.title || "";
        if (slugEl) { slugEl.value = cat.slug || ""; slugEl.disabled = true; }
        if (descEl) descEl.value = cat.description || "";
        if (sortEl) sortEl.value = cat.sort_order != null ? String(cat.sort_order) : "0";
        if (activeEl) activeEl.checked = !!cat.is_active;
        if (privateEl) privateEl.checked = !!cat.is_private;
        if (roleEl) roleEl.value = cat.required_role || "";

        if (empty) empty.hidden = true;
        if (form) form.hidden = false;
        if (editorTitle) editorTitle.textContent = "// CATEGORY " + (cat.slug || "");

        var tbody = $("manage-forum-categories-tbody");
        if (tbody) {
            [].forEach.call(tbody.querySelectorAll("tr"), function(tr) {
                tr.classList.toggle("selected", parseInt(tr.dataset.id || "0", 10) === cat.id);
            });
        }
    }

    function resetCategoryForm() {
        var idEl = $("manage-forum-category-id");
        var titleEl = $("manage-forum-category-title");
        var slugEl = $("manage-forum-category-slug");
        var descEl = $("manage-forum-category-description");
        var sortEl = $("manage-forum-category-sort");
        var activeEl = $("manage-forum-category-active");
        var privateEl = $("manage-forum-category-private");
        var roleEl = $("manage-forum-category-required-role");
        var form = $("manage-forum-category-form");
        var empty = $("manage-forum-category-editor-empty");
        var editorTitle = $("manage-forum-category-editor-title");
        var err = $("manage-forum-category-form-error");

        if (idEl) idEl.value = "";
        if (titleEl) titleEl.value = "";
        if (slugEl) { slugEl.value = ""; slugEl.disabled = false; }
        if (descEl) descEl.value = "";
        if (sortEl) sortEl.value = "0";
        if (activeEl) activeEl.checked = true;
        if (privateEl) privateEl.checked = false;
        if (roleEl) roleEl.value = "";
        if (err) { err.textContent = ""; err.hidden = true; }
        if (form) form.hidden = false;
        if (empty) empty.hidden = true;
        if (editorTitle) editorTitle.textContent = "// CATEGORY";
    }

    function initCategories() {
        var apiRef = api();
        if (!apiRef) return;
        var newBtn = $("manage-forum-category-new");
        var form = $("manage-forum-category-form");
        var resetBtn = $("manage-forum-category-reset");
        var deleteBtn = $("manage-forum-category-delete");
        var err = $("manage-forum-category-form-error");

        if (newBtn) newBtn.addEventListener("click", function() {
            resetCategoryForm();
        });

        if (form) form.addEventListener("submit", function(e) {
            e.preventDefault();
            var id = ($("manage-forum-category-id") || {}).value;
            var title = ($("manage-forum-category-title") || {}).value.trim();
            var slug = ($("manage-forum-category-slug") || {}).value.trim();
            var description = ($("manage-forum-category-description") || {}).value;
            var sort = parseInt(($("manage-forum-category-sort") || {}).value || "0", 10);
            var isActive = !!($("manage-forum-category-active") || {}).checked;
            var isPrivate = !!($("manage-forum-category-private") || {}).checked;
            var requiredRole = ($("manage-forum-category-required-role") || {}).value || null;
            if (!title || (!id && !slug)) {
                if (err) { err.textContent = "Title and slug are required."; err.hidden = false; }
                return;
            }
            var payload = {
                title: title,
                description: description,
                sort_order: sort,
                is_active: isActive,
                is_private: isPrivate,
                required_role: requiredRole
            };
            var url;
            var method;
            if (id) {
                url = "/api/v1/forum/admin/categories/" + id;
                method = "PUT";
            } else {
                url = "/api/v1/forum/admin/categories";
                method = "POST";
                payload.slug = slug;
            }
            apiRef(url, { method: method, body: JSON.stringify(payload) })
                .then(function() {
                    if (err) { err.textContent = ""; err.hidden = true; }
                    loadCategories();
                })
                .catch(function(e) {
                    if (err) {
                        err.textContent = (e && e.message) || "Save failed.";
                        err.hidden = false;
                    }
                });
        });

        if (resetBtn) resetBtn.addEventListener("click", function() {
            resetCategoryForm();
        });

        if (deleteBtn) deleteBtn.addEventListener("click", function() {
            var id = ($("manage-forum-category-id") || {}).value;
            if (!id) return;
            if (!confirm("Delete this category? Threads and posts may also be removed depending on schema.")) return;
            apiRef("/api/v1/forum/admin/categories/" + id, { method: "DELETE" })
                .then(function() {
                    resetCategoryForm();
                    loadCategories();
                })
                .catch(function(e) {
                    if (err) {
                        err.textContent = (e && e.message) || "Delete failed.";
                        err.hidden = false;
                    }
                });
        });

        loadCategories();
    }

    // --- Reports ---
    function initReports() {
        var apiRef = api();
        if (!apiRef) return;
        var loading = $("manage-forum-reports-loading");
        var errorEl = $("manage-forum-reports-error");
        var empty = $("manage-forum-reports-empty");
        var wrap = $("manage-forum-reports-table-wrap");
        var tbody = $("manage-forum-reports-tbody");
        var count = $("manage-forum-reports-count");
        var footer = $("manage-forum-reports-footer");
        var statusSel = $("manage-forum-report-status");
        var refreshBtn = $("manage-forum-report-refresh");

        function loadReports() {
            if (!apiRef) return;
            if (loading) loading.hidden = false;
            if (errorEl) { errorEl.hidden = true; errorEl.textContent = ""; }
            if (empty) empty.hidden = true;
            if (wrap) wrap.hidden = true;
            if (footer) footer.hidden = true;

            var status = statusSel ? statusSel.value : "";
            var url = "/api/v1/forum/reports";
            if (status) url += "?status=" + encodeURIComponent(status);
            apiRef(url)
                .then(function(data) {
                    var items = (data && data.items) || [];
                    if (loading) loading.hidden = true;
                    if (!items.length) {
                        if (empty) empty.hidden = false;
                        return;
                    }
                    if (tbody) {
                        tbody.innerHTML = "";
                        items.forEach(function(r) {
                            var tr = document.createElement("tr");
                            var target = (r.target_type || "?") + "#" + String(r.target_id || "");
                            var created = formatDate(r.created_at);
                            tr.innerHTML =
                                "<td>" + r.id + "</td>" +
                                "<td>" + target + "</td>" +
                                "<td>" + (r.reason || "") + "</td>" +
                                "<td>" + (r.status || "") + "</td>" +
                                "<td>" + created + "</td>" +
                                "<td>" +
                                "<button type=\"button\" class=\"btn btn-sm btn-outline\" data-status=\"open\">Open</button> " +
                                "<button type=\"button\" class=\"btn btn-sm btn-outline\" data-status=\"reviewed\">Reviewed</button> " +
                                "<button type=\"button\" class=\"btn btn-sm btn-outline\" data-status=\"resolved\">Resolved</button> " +
                                "<button type=\"button\" class=\"btn btn-sm btn-outline\" data-status=\"dismissed\">Dismiss</button>" +
                                "</td>";
                            tr.querySelectorAll("button[data-status]").forEach(function(btn) {
                                btn.addEventListener("click", function() {
                                    var newStatus = btn.getAttribute("data-status");
                                    apiRef("/api/v1/forum/reports/" + r.id, {
                                        method: "PUT",
                                        body: JSON.stringify({ status: newStatus })
                                    })
                                        .then(function() { loadReports(); })
                                        .catch(function(e) {
                                            if (errorEl) {
                                                errorEl.textContent = (e && e.message) || "Failed to update report.";
                                                errorEl.hidden = false;
                                            }
                                        });
                                });
                            });
                            tbody.appendChild(tr);
                        });
                    }
                    if (wrap) wrap.hidden = false;
                    if (count) count.textContent = items.length + " reports";
                    if (footer) footer.hidden = false;
                })
                .catch(function(e) {
                    if (loading) loading.hidden = true;
                    if (errorEl) {
                        errorEl.textContent = (e && e.message) || "Failed to load reports.";
                        errorEl.hidden = false;
                    }
                });
        }

        if (refreshBtn) refreshBtn.addEventListener("click", loadReports);
        if (statusSel) statusSel.addEventListener("change", loadReports);
        loadReports();
    }

    function init() {
        if (!window.ManageAuth) return;
        window.ManageAuth.ensureAuth().then(function(user) {
            var isAdmin = user && (user.role === "admin" || (user.allowed_features && user.allowed_features.indexOf("manage.users") >= 0));
            var categoriesCard = $("manage-forum-categories-card");
            var categoryEditor = $("manage-forum-category-editor");
            if (!isAdmin) {
                if (categoriesCard) categoriesCard.style.display = "none";
                if (categoryEditor) categoryEditor.style.display = "none";
            } else {
                if (categoriesCard) categoriesCard.style.display = "";
                if (categoryEditor) categoryEditor.style.display = "";
            }
            if (isAdmin) initCategories();
            initReports();
        }).catch(function() {});
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();

