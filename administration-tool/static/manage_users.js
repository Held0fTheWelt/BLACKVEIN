/**
 * User administration: list (admin only), search, pagination, edit (no password), role, ban, unban, delete.
 * Initializes on DOMContentLoaded; requires ManageAuth from manage_auth.js (loaded before this script in extra_scripts).
 */
(function() {
    var apiRef = null; // set at init from ManageAuth.apiFetchWithAuth
    function $(id) { return document.getElementById(id); }

    function escapeHtml(text) {
        if (!text) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function formatDateTime(iso) {
        if (!iso) return "—";
        try {
            var d = new Date(iso);
            return isNaN(d.getTime()) ? "—" : d.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
        } catch (e) { return "—"; }
    }

    var state = {
        page: 1,
        total: 0,
        perPage: 20,
        totalPages: 0,
        selectedId: null,
        items: [],
        roles: [],
        areas: [],
        currentUser: null,
    };

    function getListParams() {
        return {
            page: state.page,
            limit: state.perPage,
            q: ($("manage-users-q") || {}).value.trim() || undefined,
        };
    }

    function buildListUrl(params) {
        var parts = [];
        for (var k in params) if (params[k] !== undefined && params[k] !== "") parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(params[k]));
        return "/api/v1/users" + (parts.length ? "?" + parts.join("&") : "");
    }

    function showLoading(show) {
        var loading = $("manage-users-loading");
        var wrap = $("manage-users-table-wrap");
        var empty = $("manage-users-empty");
        var err = $("manage-users-error");
        var pag = $("manage-users-pagination");
        if (loading) loading.hidden = !show;
        if (wrap) wrap.hidden = true;
        if (empty) empty.hidden = true;
        if (err) err.hidden = true;
        if (pag) pag.hidden = true;
    }

    function showError(msg) {
        showLoading(false);
        var wrap = $("manage-users-table-wrap");
        var empty = $("manage-users-empty");
        var err = $("manage-users-error");
        var pag = $("manage-users-pagination");
        if (wrap) wrap.hidden = true;
        if (empty) empty.hidden = true;
        if (err) { err.textContent = msg || "Failed to load."; err.hidden = false; }
        if (pag) pag.hidden = true;
    }

    function renderList(items, page, total, perPage) {
        showLoading(false);
        state.items = items || [];
        state.total = total || 0;
        state.perPage = perPage || 20;
        state.totalPages = perPage ? Math.ceil(total / perPage) : 0;

        var err = $("manage-users-error");
        var empty = $("manage-users-empty");
        var wrap = $("manage-users-table-wrap");
        var tbody = $("manage-users-tbody");
        var pag = $("manage-users-pagination");
        var pagInfo = $("manage-users-pagination-info");
        var prevBtn = $("manage-users-prev");
        var nextBtn = $("manage-users-next");

        if (err) err.hidden = true;
        if (items.length === 0) {
            if (empty) empty.hidden = false;
            if (wrap) wrap.hidden = true;
            if (pag) pag.hidden = true;
            return;
        }
        if (empty) empty.hidden = true;
        if (wrap) wrap.hidden = false;
        if (tbody) {
            tbody.innerHTML = "";
            items.forEach(function(u) {
                var tr = document.createElement("tr");
                tr.dataset.id = u.id;
                if (state.selectedId === u.id) tr.classList.add("selected");
                var banText = u.is_banned ? "Yes" : "No";
                var lang = escapeHtml(u.preferred_language) || "—";
                var created = formatDateTime(u.created_at);
                var lastSeen = formatDateTime(u.last_seen_at);
                var level = typeof u.role_level === "number" ? u.role_level : (u.role_level != null ? String(u.role_level) : "—");
                tr.innerHTML =
                    "<td>" + escapeHtml(u.id) + "</td>" +
                    "<td>" + escapeHtml(u.username) + "</td>" +
                    "<td>" + escapeHtml(u.email) + "</td>" +
                    "<td>" + escapeHtml(u.role) + "</td>" +
                    "<td>" + escapeHtml(level) + "</td>" +
                    "<td>" + lang + "</td>" +
                    "<td>" + banText + "</td>" +
                    "<td>" + created + "</td>" +
                    "<td>" + lastSeen + "</td>";
                tr.addEventListener("click", function() { selectUser(u.id); });
                tbody.appendChild(tr);
            });
        }
        if (pag) {
            pag.hidden = state.totalPages <= 1;
            if (pagInfo) pagInfo.textContent = "Page " + page + " of " + (state.totalPages || 1) + " (" + total + " total)";
            if (prevBtn) prevBtn.disabled = page <= 1;
            if (nextBtn) nextBtn.disabled = page >= state.totalPages;
        }
    }

    function fetchList() {
        if (!apiRef) return;
        var params = getListParams();
        showLoading(true);
        apiRef(buildListUrl(params))
            .then(function(data) {
                var items = data.items || [];
                var total = typeof data.total === "number" ? data.total : items.length;
                var page = typeof data.page === "number" ? data.page : 1;
                var perPage = typeof data.per_page === "number" ? data.per_page : 20;
                var stored = window.ManageAuth && window.ManageAuth.getStoredUser && window.ManageAuth.getStoredUser();
                if (stored && stored.id != null) {
                    var me = items.filter(function(u) { return u.id === stored.id; })[0];
                    state.currentUser = me || stored;
                } else {
                    state.currentUser = stored;
                }
                renderList(items, page, total, perPage);
            })
            .catch(function(e) {
                showError(e.message || "Failed to load users. (Admin only)");
            });
    }

    function selectUser(id) {
        state.selectedId = id;
        var tbody = $("manage-users-tbody");
        if (tbody) {
            [].forEach.call(tbody.querySelectorAll("tr"), function(tr) {
                tr.classList.toggle("selected", parseInt(tr.dataset.id, 10) === id);
            });
        }
        var form = $("manage-users-form");
        var empty = $("manage-users-editor-empty");
        if (!id) {
            if (form) form.hidden = true;
            if (empty) empty.hidden = false;
            return;
        }
        if (empty) empty.hidden = true;
        if (form) form.hidden = false;
        apiRef("/api/v1/users/" + id)
            .then(function(user) {
                ($("manage-users-id") || {}).value = user.id;
                ($("manage-users-username") || {}).value = user.username || "";
                ($("manage-users-email") || {}).value = user.email || "";
                ($("manage-users-role") || {}).value = user.role || "user";
                var levelEl = $("manage-users-role-level");
                if (levelEl) levelEl.value = (user.role_level != null && user.role_level !== "") ? user.role_level : "0";
                var langEl = $("manage-users-preferred-language");
                if (langEl) langEl.value = user.preferred_language || "";
                var currentUser = state.currentUser || (window.ManageAuth && window.ManageAuth.getStoredUser && window.ManageAuth.getStoredUser());
                var actorLevel = (currentUser && (currentUser.role_level != null)) ? parseInt(currentUser.role_level, 10) : 0;
                var targetLevel = (user.role_level != null) ? parseInt(user.role_level, 10) : 0;
                var canEdit = !currentUser || currentUser.id === user.id || actorLevel > targetLevel;
                var saveBtn = $("manage-users-save");
                var banBtn = $("manage-users-ban-btn");
                var unbanBtn = $("manage-users-unban-btn");
                var delBtn = $("manage-users-delete-btn");
                var levelWrap = $("manage-users-role-level-wrap");
                if (saveBtn) saveBtn.disabled = !canEdit;
                if (banBtn) banBtn.disabled = !canEdit;
                if (unbanBtn) unbanBtn.disabled = !canEdit;
                if (delBtn) delBtn.disabled = !canEdit;
                if (levelWrap) levelWrap.style.display = canEdit ? "" : "none";
                var formErr = $("manage-users-form-error");
                if (!canEdit && formErr) {
                    formErr.textContent = "You cannot edit users with equal or higher role level.";
                    formErr.hidden = false;
                } else if (canEdit && formErr && formErr.textContent.indexOf("equal or higher") >= 0) {
                    formErr.hidden = true;
                    formErr.textContent = "";
                }
                var banInfo = $("manage-users-ban-info");
                var banText = $("manage-users-ban-text");
                var banBtn = $("manage-users-ban-btn");
                var unbanBtn = $("manage-users-unban-btn");
                if (user.is_banned) {
                    if (banInfo) banInfo.hidden = false;
                    if (banText) banText.textContent = (user.ban_reason || "No reason") + (user.banned_at ? " (at " + user.banned_at + ")" : "");
                    if (banBtn) banBtn.hidden = true;
                    if (unbanBtn) unbanBtn.hidden = false;
                } else {
                    if (banInfo) banInfo.hidden = true;
                    if (banBtn) banBtn.hidden = false;
                    if (unbanBtn) unbanBtn.hidden = true;
                }
                var createdEl = $("manage-users-created");
                var lastSeenEl = $("manage-users-last-seen");
                if (createdEl) createdEl.textContent = formatDateTime(user.created_at);
                if (lastSeenEl) lastSeenEl.textContent = formatDateTime(user.last_seen_at);
                var areasWrap = $("manage-users-areas-wrap");
                var areasMulti = $("manage-users-areas-multi");
                var saveAreasBtn = $("manage-users-save-areas");
                if (areasWrap) areasWrap.style.display = canEdit ? "" : "none";
                if (saveAreasBtn) saveAreasBtn.disabled = !canEdit;
                function fillAreasMulti() {
                    if (!areasMulti || !state.areas.length) return;
                    areasMulti.innerHTML = "";
                    var areaIds = user.area_ids || [];
                    state.areas.forEach(function(a) {
                        var opt = document.createElement("option");
                        opt.value = a.id;
                        opt.textContent = (a.slug || a.name || a.id);
                        opt.selected = areaIds.indexOf(a.id) >= 0;
                        areasMulti.appendChild(opt);
                    });
                }
                if (state.areas.length) fillAreasMulti();
                else apiRef("/api/v1/areas?limit=100").then(function(data) {
                    state.areas = data.items || [];
                    fillAreasMulti();
                }).catch(function() {});
                ($("manage-users-editor-title") || {}).textContent = "Edit user";
            })
            .catch(function(e) {
                showError(e.message || "Failed to load user.");
            });
    }

    function showFormError(msg) {
        var el = $("manage-users-form-error");
        var ok = $("manage-users-form-success");
        if (ok) ok.hidden = true;
        if (el) { el.textContent = msg || "Error."; el.hidden = false; }
    }

    function showFormSuccess(msg) {
        var el = $("manage-users-form-success");
        var err = $("manage-users-form-error");
        if (err) { err.hidden = true; err.textContent = ""; }
        if (el) { el.textContent = msg || "Saved."; el.hidden = false; }
        setTimeout(function() { if (el) el.hidden = true; }, 3000);
    }

    function onSave(e) {
        e.preventDefault();
        var id = ($("manage-users-id") || {}).value;
        if (!id) return;
        var username = ($("manage-users-username") || {}).value.trim();
        if (!username) {
            showFormError("Username is required.");
            return;
        }
        var payload = {
            username: username,
            email: ($("manage-users-email") || {}).value.trim() || null,
            role: ($("manage-users-role") || {}).value || "user",
            preferred_language: ($("manage-users-preferred-language") || {}).value || null,
        };
        var levelEl = $("manage-users-role-level");
        if (levelEl && levelEl.value !== "" && levelEl.value != null) {
            var l = parseInt(levelEl.value, 10);
            if (!isNaN(l)) payload.role_level = l;
        }
        if (payload.preferred_language === "") payload.preferred_language = null;
        var saveBtn = $("manage-users-save");
        if (saveBtn) saveBtn.disabled = true;
        apiRef("/api/v1/users/" + id, { method: "PUT", body: JSON.stringify(payload) })
            .then(function(user) {
                showFormSuccess("Updated.");
                if (saveBtn) saveBtn.disabled = false;
                fetchList();
                selectUser(user.id);
            })
            .catch(function(e) {
                showFormError(e.message || "Update failed.");
                if (saveBtn) saveBtn.disabled = false;
            });
    }

    function onBan() {
        var id = ($("manage-users-id") || {}).value;
        if (!id) return;
        var reason = window.prompt("Ban reason (optional):");
        if (reason === null) return;
        var payload = reason ? { reason: reason } : {};
        apiRef("/api/v1/users/" + id + "/ban", { method: "POST", body: JSON.stringify(payload) })
            .then(function() {
                showFormSuccess("User banned.");
                selectUser(parseInt(id, 10));
                fetchList();
            })
            .catch(function(e) {
                showFormError(e.message || "Ban failed.");
            });
    }

    function onUnban() {
        var id = ($("manage-users-id") || {}).value;
        if (!id) return;
        apiRef("/api/v1/users/" + id + "/unban", { method: "POST" })
            .then(function() {
                showFormSuccess("User unbanned.");
                selectUser(parseInt(id, 10));
                fetchList();
            })
            .catch(function(e) {
                showFormError(e.message || "Unban failed.");
            });
    }

    function onSaveAreas() {
        var id = ($("manage-users-id") || {}).value;
        if (!id) return;
        var sel = $("manage-users-areas-multi");
        var areaIds = [];
        if (sel) {
            for (var i = 0; i < sel.options.length; i++) {
                if (sel.options[i].selected) areaIds.push(parseInt(sel.options[i].value, 10));
            }
        }
        var btn = $("manage-users-save-areas");
        if (btn) btn.disabled = true;
        apiRef("/api/v1/users/" + id + "/areas", { method: "PUT", body: JSON.stringify({ area_ids: areaIds }) })
            .then(function() {
                showFormSuccess("Areas updated.");
                if (btn) btn.disabled = false;
                selectUser(parseInt(id, 10));
                fetchList();
            })
            .catch(function(e) {
                showFormError(e.message || "Update areas failed.");
                if (btn) btn.disabled = false;
            });
    }

    function onDelete() {
        var id = ($("manage-users-id") || {}).value;
        if (!id) return;
        if (!confirm("Delete this user? This cannot be undone.")) return;
        apiRef("/api/v1/users/" + id, { method: "DELETE" })
            .then(function() {
                state.selectedId = null;
                var form = $("manage-users-form");
                var empty = $("manage-users-editor-empty");
                if (form) form.hidden = true;
                if (empty) empty.hidden = false;
                ($("manage-users-editor-title") || {}).textContent = "User detail";
                fetchList();
            })
            .catch(function(e) {
                showFormError(e.message || "Delete failed.");
            });
    }

    function initUsersPage() {
        var api = window.ManageAuth && window.ManageAuth.apiFetchWithAuth;
        if (!api) {
            console.error("[manage_users] ManageAuth.apiFetchWithAuth not available. Ensure manage_auth.js loads before this script.");
            var errEl = $("manage-users-error");
            if (errEl) { errEl.textContent = "Auth not loaded. Refresh the page."; errEl.hidden = false; }
            return;
        }
        apiRef = api;

        var applyBtn = $("manage-users-apply");
        var form = $("manage-users-form");
        var saveBtn = $("manage-users-save");
        var banBtn = $("manage-users-ban-btn");
        var unbanBtn = $("manage-users-unban-btn");
        var delBtn = $("manage-users-delete-btn");
        var prevBtn = $("manage-users-prev");
        var nextBtn = $("manage-users-next");

        var searchInput = $("manage-users-q");
        if (applyBtn) applyBtn.addEventListener("click", function() { state.page = 1; fetchList(); });
        if (searchInput) searchInput.addEventListener("keydown", function(e) {
            if (e.key === "Enter") { e.preventDefault(); state.page = 1; fetchList(); }
        });
        if (form) form.addEventListener("submit", onSave);
        var saveAreasBtn = $("manage-users-save-areas");
        if (saveAreasBtn) saveAreasBtn.addEventListener("click", onSaveAreas);
        if (banBtn) banBtn.addEventListener("click", onBan);
        if (unbanBtn) unbanBtn.addEventListener("click", onUnban);
        if (delBtn) delBtn.addEventListener("click", onDelete);
        if (prevBtn) prevBtn.addEventListener("click", function() {
            if (state.page > 1) { state.page--; fetchList(); }
        });
        if (nextBtn) nextBtn.addEventListener("click", function() {
            if (state.page < state.totalPages) { state.page++; fetchList(); }
        });

        function fetchRoles() {
            apiRef("/api/v1/roles?limit=100")
                .then(function(data) {
                    var items = data.items || [];
                    state.roles = items;
                    var sel = $("manage-users-role");
                    if (sel && items.length) {
                        var current = sel.value;
                        sel.innerHTML = "";
                        items.forEach(function(r) {
                            var opt = document.createElement("option");
                            opt.value = r.name;
                            opt.textContent = r.name;
                            sel.appendChild(opt);
                        });
                        if (current) sel.value = current;
                    }
                })
                .catch(function() {});
        }
        function fetchAreas() {
            apiRef("/api/v1/areas?limit=100")
                .then(function(data) {
                    state.areas = data.items || [];
                })
                .catch(function() {});
        }
        fetchRoles();
        fetchAreas();
        fetchList();
    }

    function run() {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", initUsersPage);
        } else {
            initUsersPage();
        }
    }
    run();
})();
