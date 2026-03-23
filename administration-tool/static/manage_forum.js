(function() {
    function $(id) { return id ? document.getElementById(id) : null; }

    function formatDate(iso) {
        if (!iso) return "";
        var d = new Date(iso);
        return isNaN(d.getTime()) ? "" : d.toLocaleString();
    }

    function escapeHtml(s) {
        if (s == null) return "";
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
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
                            "<td>" + escapeHtml(cat.title || "") + "</td>" +
                            "<td>" + escapeHtml(cat.slug || "") + "</td>" +
                            "<td>" + (cat.sort_order != null ? String(cat.sort_order) : "") + "</td>" +
                            "<td>" + (cat.is_active ? "Yes" : "No") + "</td>" +
                            "<td>" + (cat.is_private ? "Yes" : "No") + "</td>" +
                            "<td>" + escapeHtml(cat.required_role || "") + "</td>";
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
        var targetTypeSel = $("manage-forum-report-target-type");
        var refreshBtn = $("manage-forum-report-refresh");
        var loadMoreBtn = $("manage-forum-reports-load-more");
        var bulkBar = $("manage-forum-reports-bulk-bar");
        var selectAllCb = $("manage-forum-reports-select-all");
        var theadCheck = $("manage-forum-reports-thead-check");
        var bulkAction = $("manage-forum-reports-bulk-action");
        var bulkNote = $("manage-forum-reports-bulk-note");
        var bulkApply = $("manage-forum-reports-bulk-apply");

        var currentPage = 1;
        var currentTotal = 0;
        var pageLimit = 20;

        function getSelectedIds() {
            var ids = [];
            if (tbody) {
                tbody.querySelectorAll("input.report-check:checked").forEach(function(cb) {
                    ids.push(parseInt(cb.value, 10));
                });
            }
            return ids;
        }

        function syncSelectAll() {
            var all = tbody ? tbody.querySelectorAll("input.report-check") : [];
            var checked = tbody ? tbody.querySelectorAll("input.report-check:checked") : [];
            var allChecked = all.length > 0 && all.length === checked.length;
            if (selectAllCb) selectAllCb.checked = allChecked;
            if (theadCheck) theadCheck.checked = allChecked;
        }

        function loadReports(append) {
            if (!apiRef) return;
            if (!append) {
                currentPage = 1;
                if (loading) loading.hidden = false;
                if (empty) empty.hidden = true;
                if (wrap) wrap.hidden = true;
                if (footer) footer.hidden = true;
                if (bulkBar) bulkBar.hidden = true;
            }
            if (errorEl) { errorEl.hidden = true; errorEl.textContent = ""; }

            var status = statusSel ? statusSel.value : "";
            var targetType = targetTypeSel ? targetTypeSel.value : "";
            var params = ["page=" + currentPage, "limit=" + pageLimit];
            if (status) params.push("status=" + encodeURIComponent(status));
            if (targetType) params.push("target_type=" + encodeURIComponent(targetType));
            var url = "/api/v1/forum/reports?" + params.join("&");
            apiRef(url)
                .then(function(data) {
                    var items = (data && data.items) || [];
                    currentTotal = data.total || 0;
                    if (loading) loading.hidden = true;
                    if (!append && !items.length) {
                        if (empty) empty.hidden = false;
                        return;
                    }
                    if (tbody && !append) tbody.innerHTML = "";
                    if (tbody) {
                        items.forEach(function(r) {
                            var tr = document.createElement("tr");
                            var target = (r.target_type || "?") + "#" + String(r.target_id || "");
                            var created = formatDate(r.created_at);
                            var noteSnippet = escapeHtml(r.resolution_note ? r.resolution_note.substring(0, 40) + (r.resolution_note.length > 40 ? "..." : "") : "");
                            tr.innerHTML =
                                "<td><input type=\"checkbox\" class=\"report-check\" value=\"" + r.id + "\"></td>" +
                                "<td>" + r.id + "</td>" +
                                "<td>" + target + "</td>" +
                                "<td>" + escapeHtml(r.reason || "") + "</td>" +
                                "<td class=\"mono\" style=\"font-size:0.85em;\">" + noteSnippet + "</td>" +
                                "<td>" + (r.status || "") + "</td>" +
                                "<td>" + created + "</td>" +
                                "<td>" +
                                "<button type=\"button\" class=\"btn btn-sm btn-outline\" data-status=\"open\">Open</button> " +
                                "<button type=\"button\" class=\"btn btn-sm btn-outline\" data-status=\"reviewed\">Reviewed</button> " +
                                "<button type=\"button\" class=\"btn btn-sm btn-outline\" data-status=\"escalated\">Escalate</button> " +
                                "<button type=\"button\" class=\"btn btn-sm btn-outline\" data-status=\"resolved\">Resolve</button> " +
                                "<button type=\"button\" class=\"btn btn-sm btn-outline\" data-status=\"dismissed\">Dismiss</button>" +
                                "</td>";
                            tr.querySelectorAll("button[data-status]").forEach(function(btn) {
                                btn.addEventListener("click", function() {
                                    var newStatus = btn.getAttribute("data-status");
                                    var noteInput = (newStatus === "resolved" || newStatus === "dismissed") ? prompt("Resolution note (optional):") : null;
                                    var body = { status: newStatus };
                                    if (noteInput) body.resolution_note = noteInput;
                                    apiRef("/api/v1/forum/reports/" + r.id, {
                                        method: "PUT",
                                        body: JSON.stringify(body)
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
                            tr.querySelector("input.report-check").addEventListener("change", syncSelectAll);
                            tbody.appendChild(tr);
                        });
                    }
                    if (wrap) wrap.hidden = false;
                    if (bulkBar) bulkBar.hidden = false;
                    var loaded = tbody ? tbody.querySelectorAll("tr").length : 0;
                    if (count) count.textContent = loaded + " / " + currentTotal + " reports";
                    if (footer) footer.hidden = false;
                    if (loadMoreBtn) loadMoreBtn.hidden = (loaded >= currentTotal);
                })
                .catch(function(e) {
                    if (loading) loading.hidden = true;
                    if (errorEl) {
                        errorEl.textContent = (e && e.message) || "Failed to load reports.";
                        errorEl.hidden = false;
                    }
                });
        }

        if (loadMoreBtn) loadMoreBtn.addEventListener("click", function() {
            currentPage++;
            loadReports(true);
        });

        function toggleAll(checked) {
            if (tbody) {
                tbody.querySelectorAll("input.report-check").forEach(function(cb) { cb.checked = checked; });
            }
        }
        if (selectAllCb) selectAllCb.addEventListener("change", function() { toggleAll(selectAllCb.checked); if (theadCheck) theadCheck.checked = selectAllCb.checked; });
        if (theadCheck) theadCheck.addEventListener("change", function() { toggleAll(theadCheck.checked); if (selectAllCb) selectAllCb.checked = theadCheck.checked; });

        if (bulkApply) bulkApply.addEventListener("click", function() {
            var ids = getSelectedIds();
            var action = bulkAction ? bulkAction.value : "";
            if (!ids.length || !action) { alert("Select reports and an action."); return; }
            var body = { report_ids: ids, status: action };
            var note = bulkNote ? bulkNote.value.trim() : "";
            if (note) body.resolution_note = note;
            apiRef("/api/v1/forum/reports/bulk-status", {
                method: "POST",
                body: JSON.stringify(body)
            })
                .then(function() { loadReports(); })
                .catch(function(e) {
                    if (errorEl) {
                        errorEl.textContent = (e && e.message) || "Bulk update failed.";
                        errorEl.hidden = false;
                    }
                });
        });

        if (refreshBtn) refreshBtn.addEventListener("click", function() { loadReports(); });
        if (statusSel) statusSel.addEventListener("change", function() { loadReports(); });
        if (targetTypeSel) targetTypeSel.addEventListener("change", function() { loadReports(); });
        loadReports();
    }

    function forumThreadUrl(slug) {
        if (!slug) return "#";
        return "/forum/threads/" + encodeURIComponent(slug);
    }

    function initModerationDashboard() {
        var apiRef = api();
        if (!apiRef) return;
        var card = $("manage-forum-dashboard-card");
        if (!card) return;
        card.hidden = false;

        var loading = $("manage-forum-dashboard-loading");
        var errorEl = $("manage-forum-dashboard-error");
        var content = $("manage-forum-dashboard-content");
        var refreshBtn = $("manage-forum-dashboard-refresh");

        function setError(msg) {
            if (errorEl) { errorEl.textContent = msg || ""; errorEl.hidden = !msg; }
        }

        function loadMetrics() {
            apiRef("/api/v1/forum/moderation/metrics")
                .then(function(m) {
                    var el = $("manage-forum-metrics");
                    if (el) {
                        el.innerHTML =
                            "<span class=\"manage-metric\">Open reports: <strong>" + (m.open_reports || 0) + "</strong></span> " +
                            "<span class=\"manage-metric\">Hidden posts: <strong>" + (m.hidden_posts || 0) + "</strong></span> " +
                            "<span class=\"manage-metric\">Locked threads: <strong>" + (m.locked_threads || 0) + "</strong></span> " +
                            "<span class=\"manage-metric\">Pinned threads: <strong>" + (m.pinned_threads || 0) + "</strong></span>";
                    }
                })
                .catch(function() {});
        }

        function loadOpenReports() {
            var wrap = $("manage-forum-open-reports-wrap");
            var loadEl = $("manage-forum-open-reports-loading");
            var emptyEl = $("manage-forum-open-reports-empty");
            if (loadEl) loadEl.hidden = false;
            if (emptyEl) emptyEl.hidden = true;
            if (wrap) { wrap.hidden = true; wrap.innerHTML = ""; }
            apiRef("/api/v1/forum/moderation/recent-reports?limit=15")
                .then(function(data) {
                    if (loadEl) loadEl.hidden = true;
                    var items = (data && data.items) || [];
                    if (!items.length) {
                        if (emptyEl) emptyEl.hidden = false;
                        return;
                    }
                    var table = document.createElement("table");
                    table.className = "data-table";
                    table.innerHTML = "<thead><tr><th>Target</th><th>Reason</th><th>Created</th><th>Actions</th></tr></thead><tbody></tbody>";
                    items.forEach(function(r) {
                        var slug = r.thread_slug;
                        var link = slug ? "<a href=\"" + forumThreadUrl(slug) + "\">" + escapeHtml(r.target_title || r.target_type + "#" + r.target_id) + "</a>" : (r.target_type + "#" + r.target_id);
                        var tr = document.createElement("tr");
                        tr.innerHTML =
                            "<td>" + link + "</td>" +
                            "<td>" + escapeHtml((r.reason || "").substring(0, 60)) + (r.reason && r.reason.length > 60 ? "…" : "") + "</td>" +
                            "<td>" + formatDate(r.created_at) + "</td>" +
                            "<td>" +
                            "<button type=\"button\" class=\"btn btn-sm btn-outline\" data-status=\"reviewed\">Reviewed</button> " +
                            "<button type=\"button\" class=\"btn btn-sm btn-outline\" data-status=\"resolved\">Resolved</button> " +
                            "<button type=\"button\" class=\"btn btn-sm btn-outline\" data-status=\"dismissed\">Dismiss</button>" +
                            "</td>";
                        tr.querySelectorAll("button[data-status]").forEach(function(btn) {
                            btn.addEventListener("click", function() {
                                var newStatus = btn.getAttribute("data-status");
                                apiRef("/api/v1/forum/reports/" + r.id, { method: "PUT", body: JSON.stringify({ status: newStatus }) })
                                    .then(function() { loadOpenReports(); loadMetrics(); loadHandled(); })
                                    .catch(function(e) { setError((e && e.message) || "Failed to update report."); });
                            });
                        });
                        table.querySelector("tbody").appendChild(tr);
                    });
                    if (wrap) { wrap.appendChild(table); wrap.hidden = false; }
                })
                .catch(function(e) {
                    if (loadEl) loadEl.hidden = true;
                    setError((e && e.message) || "Failed to load open reports.");
                });
        }

        function loadHandled() {
            var wrap = $("manage-forum-handled-wrap");
            var loadEl = $("manage-forum-handled-loading");
            var emptyEl = $("manage-forum-handled-empty");
            if (loadEl) loadEl.hidden = false;
            if (emptyEl) emptyEl.hidden = true;
            if (wrap) { wrap.hidden = true; wrap.innerHTML = ""; }
            apiRef("/api/v1/forum/moderation/recently-handled?limit=10")
                .then(function(data) {
                    if (loadEl) loadEl.hidden = true;
                    var items = (data && data.items) || [];
                    if (!items.length) {
                        if (emptyEl) emptyEl.hidden = false;
                        return;
                    }
                    var table = document.createElement("table");
                    table.className = "data-table";
                    table.innerHTML = "<thead><tr><th>Target</th><th>Status</th><th>Handled</th></tr></thead><tbody></tbody>";
                    items.forEach(function(r) {
                        var slug = r.thread_slug;
                        var link = slug ? "<a href=\"" + forumThreadUrl(slug) + "\">" + escapeHtml(r.target_title || r.target_type + "#" + r.target_id) + "</a>" : (r.target_type + "#" + r.target_id);
                        var tr = document.createElement("tr");
                        tr.innerHTML =
                            "<td>" + link + "</td>" +
                            "<td>" + (r.status || "") + "</td>" +
                            "<td>" + formatDate(r.handled_at) + "</td>";
                        table.querySelector("tbody").appendChild(tr);
                    });
                    if (wrap) { wrap.appendChild(table); wrap.hidden = false; }
                })
                .catch(function() {
                    if (loadEl) loadEl.hidden = true;
                    if (emptyEl) emptyEl.hidden = false;
                });
        }

        function loadLocked() {
            var wrap = $("manage-forum-locked-wrap");
            var loadEl = $("manage-forum-locked-loading");
            var emptyEl = $("manage-forum-locked-empty");
            var bulkBar = $("manage-forum-locked-bulk-bar");
            var selectAllCb = $("manage-forum-locked-select-all");
            var bulkUnlockBtn = $("manage-forum-locked-bulk-unlock");
            if (loadEl) loadEl.hidden = false;
            if (emptyEl) emptyEl.hidden = true;
            if (wrap) { wrap.hidden = true; wrap.innerHTML = ""; }
            if (bulkBar) bulkBar.hidden = true;
            apiRef("/api/v1/forum/moderation/locked-threads?limit=20")
                .then(function(data) {
                    if (loadEl) loadEl.hidden = true;
                    var items = (data && data.items) || [];
                    if (!items.length) {
                        if (emptyEl) emptyEl.hidden = false;
                        return;
                    }
                    var table = document.createElement("table");
                    table.className = "data-table";
                    table.innerHTML = "<thead><tr><th style=\"width:2rem;\"><input type=\"checkbox\" class=\"locked-thead-check\"></th><th>Thread</th><th>Category</th><th>Updated</th></tr></thead><tbody></tbody>";
                    items.forEach(function(t) {
                        var link = "<a href=\"" + forumThreadUrl(t.slug) + "\">" + escapeHtml(t.title || "") + "</a>";
                        var tr = document.createElement("tr");
                        tr.innerHTML = "<td><input type=\"checkbox\" class=\"locked-check\" value=\"" + t.id + "\"></td><td>" + link + "</td><td>" + escapeHtml(t.category_slug || "") + "</td><td>" + formatDate(t.updated_at) + "</td>";
                        table.querySelector("tbody").appendChild(tr);
                    });
                    var theadCb = table.querySelector(".locked-thead-check");
                    if (theadCb) {
                        theadCb.addEventListener("change", function() {
                            table.querySelectorAll(".locked-check").forEach(function(cb) { cb.checked = theadCb.checked; });
                            if (selectAllCb) selectAllCb.checked = theadCb.checked;
                        });
                    }
                    if (selectAllCb) {
                        selectAllCb.onclick = function() {
                            table.querySelectorAll(".locked-check").forEach(function(cb) { cb.checked = selectAllCb.checked; });
                            if (theadCb) theadCb.checked = selectAllCb.checked;
                        };
                    }
                    if (bulkUnlockBtn) {
                        bulkUnlockBtn.onclick = function() {
                            var ids = [];
                            table.querySelectorAll(".locked-check:checked").forEach(function(cb) { ids.push(parseInt(cb.value, 10)); });
                            if (!ids.length) { alert("Select threads to unlock."); return; }
                            apiRef("/api/v1/forum/moderation/bulk-threads/status", {
                                method: "POST",
                                body: JSON.stringify({ thread_ids: ids, lock: false })
                            }).then(function() { loadLocked(); loadMetrics(); }).catch(function(e) { setError((e && e.message) || "Bulk unlock failed."); });
                        };
                    }
                    if (wrap) { wrap.appendChild(table); wrap.hidden = false; }
                    if (bulkBar) bulkBar.hidden = false;
                })
                .catch(function() { if (loadEl) loadEl.hidden = true; });
        }

        function loadPinned() {
            var wrap = $("manage-forum-pinned-wrap");
            var loadEl = $("manage-forum-pinned-loading");
            var emptyEl = $("manage-forum-pinned-empty");
            if (loadEl) loadEl.hidden = false;
            if (emptyEl) emptyEl.hidden = true;
            if (wrap) { wrap.hidden = true; wrap.innerHTML = ""; }
            apiRef("/api/v1/forum/moderation/pinned-threads?limit=20")
                .then(function(data) {
                    if (loadEl) loadEl.hidden = true;
                    var items = (data && data.items) || [];
                    if (!items.length) {
                        if (emptyEl) emptyEl.hidden = false;
                        return;
                    }
                    var table = document.createElement("table");
                    table.className = "data-table";
                    table.innerHTML = "<thead><tr><th>Thread</th><th>Category</th><th>Updated</th></tr></thead><tbody></tbody>";
                    items.forEach(function(t) {
                        var link = "<a href=\"" + forumThreadUrl(t.slug) + "\">" + escapeHtml(t.title || "") + "</a>";
                        var tr = document.createElement("tr");
                        tr.innerHTML = "<td>" + link + "</td><td>" + escapeHtml(t.category_slug || "") + "</td><td>" + formatDate(t.updated_at) + "</td>";
                        table.querySelector("tbody").appendChild(tr);
                    });
                    if (wrap) { wrap.appendChild(table); wrap.hidden = false; }
                })
                .catch(function() { if (loadEl) loadEl.hidden = true; });
        }

        function loadHidden() {
            var wrap = $("manage-forum-hidden-wrap");
            var loadEl = $("manage-forum-hidden-loading");
            var emptyEl = $("manage-forum-hidden-empty");
            var bulkBar = $("manage-forum-hidden-bulk-bar");
            var selectAllCb = $("manage-forum-hidden-select-all");
            var bulkUnhideBtn = $("manage-forum-hidden-bulk-unhide");
            if (loadEl) loadEl.hidden = false;
            if (emptyEl) emptyEl.hidden = true;
            if (wrap) { wrap.hidden = true; wrap.innerHTML = ""; }
            if (bulkBar) bulkBar.hidden = true;
            apiRef("/api/v1/forum/moderation/hidden-posts?limit=20")
                .then(function(data) {
                    if (loadEl) loadEl.hidden = true;
                    var items = (data && data.items) || [];
                    if (!items.length) {
                        if (emptyEl) emptyEl.hidden = false;
                        return;
                    }
                    var table = document.createElement("table");
                    table.className = "data-table";
                    table.innerHTML = "<thead><tr><th style=\"width:2rem;\"><input type=\"checkbox\" class=\"hidden-thead-check\"></th><th>Thread</th><th>Snippet</th><th>Updated</th></tr></thead><tbody></tbody>";
                    items.forEach(function(p) {
                        var link = p.thread_slug ? "<a href=\"" + forumThreadUrl(p.thread_slug) + "\">" + escapeHtml(p.thread_title || p.thread_slug) + "</a>" : ("post#" + p.id);
                        var tr = document.createElement("tr");
                        tr.innerHTML = "<td><input type=\"checkbox\" class=\"hidden-check\" value=\"" + p.id + "\"></td><td>" + link + "</td><td>" + escapeHtml(p.content_snippet || "") + "</td><td>" + formatDate(p.updated_at) + "</td>";
                        table.querySelector("tbody").appendChild(tr);
                    });
                    var theadCb = table.querySelector(".hidden-thead-check");
                    if (theadCb) {
                        theadCb.addEventListener("change", function() {
                            table.querySelectorAll(".hidden-check").forEach(function(cb) { cb.checked = theadCb.checked; });
                            if (selectAllCb) selectAllCb.checked = theadCb.checked;
                        });
                    }
                    if (selectAllCb) {
                        selectAllCb.onclick = function() {
                            table.querySelectorAll(".hidden-check").forEach(function(cb) { cb.checked = selectAllCb.checked; });
                            if (theadCb) theadCb.checked = selectAllCb.checked;
                        };
                    }
                    if (bulkUnhideBtn) {
                        bulkUnhideBtn.onclick = function() {
                            var ids = [];
                            table.querySelectorAll(".hidden-check:checked").forEach(function(cb) { ids.push(parseInt(cb.value, 10)); });
                            if (!ids.length) { alert("Select posts to unhide."); return; }
                            apiRef("/api/v1/forum/moderation/bulk-posts/hide", {
                                method: "POST",
                                body: JSON.stringify({ post_ids: ids, hidden: false })
                            }).then(function() { loadHidden(); loadMetrics(); }).catch(function(e) { setError((e && e.message) || "Bulk unhide failed."); });
                        };
                    }
                    if (wrap) { wrap.appendChild(table); wrap.hidden = false; }
                    if (bulkBar) bulkBar.hidden = false;
                })
                .catch(function() { if (loadEl) loadEl.hidden = true; });
        }

        function loadAll() {
            setError("");
            if (loading) loading.hidden = false;
            if (content) content.hidden = true;
            apiRef("/api/v1/forum/moderation/metrics")
                .then(function(m) {
                    if (loading) loading.hidden = true;
                    if (content) content.hidden = false;
                    loadMetrics();
                    loadOpenReports();
                    loadHandled();
                    loadLocked();
                    loadPinned();
                    loadHidden();
                })
                .catch(function(e) {
                    if (loading) loading.hidden = true;
                    setError((e && e.message) || "Failed to load dashboard.");
                });
        }

        if (refreshBtn) refreshBtn.addEventListener("click", loadAll);
        loadAll();
    }

    function initModerationLog() {
        var apiRef = api();
        if (!apiRef) return;
        var card = $("manage-forum-modlog-card");
        if (!card) return;
        card.hidden = false;

        var loading = $("manage-forum-modlog-loading");
        var errorEl = $("manage-forum-modlog-error");
        var empty = $("manage-forum-modlog-empty");
        var wrap = $("manage-forum-modlog-table-wrap");
        var tbody = $("manage-forum-modlog-tbody");
        var countEl = $("manage-forum-modlog-count");
        var footer = $("manage-forum-modlog-footer");
        var loadMoreBtn = $("manage-forum-modlog-load-more");
        var refreshBtn = $("manage-forum-modlog-refresh");

        var currentPage = 1;
        var currentTotal = 0;
        var pageLimit = 30;

        function loadLog(append) {
            if (!append) {
                currentPage = 1;
                if (loading) loading.hidden = false;
                if (empty) empty.hidden = true;
                if (wrap) wrap.hidden = true;
                if (footer) footer.hidden = true;
            }
            if (errorEl) { errorEl.hidden = true; errorEl.textContent = ""; }

            var url = "/api/v1/forum/moderation/log?page=" + currentPage + "&limit=" + pageLimit;
            apiRef(url)
                .then(function(data) {
                    var items = (data && data.items) || [];
                    currentTotal = data.total || 0;
                    if (loading) loading.hidden = true;
                    if (!append && !items.length) {
                        if (empty) empty.hidden = false;
                        return;
                    }
                    if (tbody && !append) { while (tbody.firstChild) tbody.removeChild(tbody.firstChild); }
                    if (tbody) {
                        items.forEach(function(entry) {
                            var tr = document.createElement("tr");
                            var cells = [
                                escapeHtml(entry.actor_username_snapshot || "system"),
                                escapeHtml(entry.action || ""),
                                escapeHtml((entry.target_type || "") + (entry.target_id ? "#" + entry.target_id : "")),
                                escapeHtml((entry.message || "").substring(0, 80)),
                                formatDate(entry.created_at)
                            ];
                            cells.forEach(function(text) {
                                var td = document.createElement("td");
                                td.textContent = text;
                                tr.appendChild(td);
                            });
                            tbody.appendChild(tr);
                        });
                    }
                    if (wrap) wrap.hidden = false;
                    var loaded = tbody ? tbody.querySelectorAll("tr").length : 0;
                    if (countEl) countEl.textContent = loaded + " / " + currentTotal + " entries";
                    if (footer) footer.hidden = false;
                    if (loadMoreBtn) loadMoreBtn.hidden = (loaded >= currentTotal);
                })
                .catch(function(e) {
                    if (loading) loading.hidden = true;
                    if (errorEl) {
                        errorEl.textContent = (e && e.message) || "Failed to load moderation log.";
                        errorEl.hidden = false;
                    }
                });
        }

        if (loadMoreBtn) loadMoreBtn.addEventListener("click", function() {
            currentPage++;
            loadLog(true);
        });
        if (refreshBtn) refreshBtn.addEventListener("click", function() { loadLog(); });
        loadLog();
    }

    // --- Tags ---
    function initTags() {
        var apiRef = api();
        if (!apiRef) return;
        var loading = $("manage-forum-tags-loading");
        var errorEl = $("manage-forum-tags-error");
        var empty = $("manage-forum-tags-empty");
        var wrap = $("manage-forum-tags-table-wrap");
        var tbody = $("manage-forum-tags-tbody");
        var count = $("manage-forum-tags-count");
        var footer = $("manage-forum-tags-footer");
        var searchInput = $("manage-forum-tags-search");
        var refreshBtn = $("manage-forum-tags-refresh");

        function loadTags() {
            if (!apiRef) return;
            if (loading) loading.hidden = false;
            if (errorEl) { errorEl.hidden = true; errorEl.textContent = ""; }
            if (empty) empty.hidden = true;
            if (wrap) wrap.hidden = true;
            if (footer) footer.hidden = true;

            var q = searchInput ? searchInput.value.trim() : "";
            var url = "/api/v1/forum/tags?limit=100";
            if (q) url += "&q=" + encodeURIComponent(q);
            apiRef(url)
                .then(function(data) {
                    var items = (data && data.items) || [];
                    if (loading) loading.hidden = true;
                    if (!items.length) {
                        if (empty) empty.hidden = false;
                        return;
                    }
                    if (tbody) {
                        while (tbody.firstChild) tbody.removeChild(tbody.firstChild);
                        items.forEach(function(tag) {
                            var tr = document.createElement("tr");
                            var tdSlug = document.createElement("td");
                            tdSlug.textContent = tag.slug || "";
                            var tdLabel = document.createElement("td");
                            tdLabel.textContent = tag.label || "";
                            var tdCount = document.createElement("td");
                            tdCount.textContent = String(tag.thread_count || 0);
                            var tdCreated = document.createElement("td");
                            tdCreated.textContent = formatDate(tag.created_at);
                            var tdActions = document.createElement("td");
                            if (tag.thread_count === 0) {
                                var delBtn = document.createElement("button");
                                delBtn.type = "button";
                                delBtn.className = "btn btn-sm btn-outline";
                                delBtn.textContent = "Delete";
                                delBtn.addEventListener("click", function() {
                                    if (!confirm("Delete tag '" + (tag.slug || "") + "'?")) return;
                                    apiRef("/api/v1/forum/tags/" + tag.id, { method: "DELETE" })
                                        .then(function() { loadTags(); })
                                        .catch(function(e) {
                                            if (errorEl) {
                                                errorEl.textContent = (e && e.message) || "Delete failed.";
                                                errorEl.hidden = false;
                                            }
                                        });
                                });
                                tdActions.appendChild(delBtn);
                            } else {
                                tdActions.textContent = "In use";
                            }
                            tr.appendChild(tdSlug);
                            tr.appendChild(tdLabel);
                            tr.appendChild(tdCount);
                            tr.appendChild(tdCreated);
                            tr.appendChild(tdActions);
                            tbody.appendChild(tr);
                        });
                    }
                    if (wrap) wrap.hidden = false;
                    if (count) count.textContent = items.length + " tags";
                    if (footer) footer.hidden = false;
                })
                .catch(function(e) {
                    if (loading) loading.hidden = true;
                    if (errorEl) {
                        errorEl.textContent = (e && e.message) || "Failed to load tags.";
                        errorEl.hidden = false;
                    }
                });
        }

        if (refreshBtn) refreshBtn.addEventListener("click", loadTags);
        if (searchInput) {
            var debounceTimer;
            searchInput.addEventListener("input", function() {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(loadTags, 300);
            });
        }
        loadTags();
    }

    function init() {
        if (!window.ManageAuth) return;
        window.ManageAuth.ensureAuth().then(function(user) {
            var isAdmin = user && (user.role === "admin" || (user.allowed_features && user.allowed_features.indexOf("manage.users") >= 0));
            var isModeratorOrAdmin = user && (user.role === "moderator" || user.role === "admin");
            var categoriesCard = $("manage-forum-categories-card");
            var categoryEditor = $("manage-forum-category-editor");
            var tagsCard = $("manage-forum-tags-card");
            if (!isAdmin) {
                if (categoriesCard) categoriesCard.style.display = "none";
                if (categoryEditor) categoryEditor.style.display = "none";
            } else {
                if (categoriesCard) categoriesCard.style.display = "";
                if (categoryEditor) categoryEditor.style.display = "";
            }
            if (isAdmin) initCategories();
            if (isModeratorOrAdmin) {
                initTags();
                if (tagsCard) tagsCard.style.display = "";
            } else {
                if (tagsCard) tagsCard.style.display = "none";
            }
            initReports();
            if (isModeratorOrAdmin) {
                initModerationDashboard();
                initModerationLog();
            }
        }).catch(function() {});
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();

