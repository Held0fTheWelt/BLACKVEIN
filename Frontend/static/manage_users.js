/**
 * User administration: list (admin only), search, pagination, edit (no password), role, ban, unban, delete.
 * Initializes on DOMContentLoaded; requires ManageAuth from manage_auth.js (loaded before this script in extra_scripts).
 */
(function() {
    var apiRef = null; // set at init from ManageAuth.apiFetchWithAuth
    function $(id) { return document.getElementById(id); }

    var state = {
        page: 1,
        total: 0,
        perPage: 20,
        totalPages: 0,
        selectedId: null,
        items: [],
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
                var lang = (u.preferred_language || "").replace(/</g, "&lt;") || "—";
                tr.innerHTML =
                    "<td>" + (u.id || "") + "</td>" +
                    "<td>" + (u.username || "").replace(/</g, "&lt;") + "</td>" +
                    "<td>" + (u.email || "").replace(/</g, "&lt;") + "</td>" +
                    "<td>" + (u.role || "").replace(/</g, "&lt;") + "</td>" +
                    "<td>" + lang + "</td>" +
                    "<td>" + banText + "</td>";
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
                var langEl = $("manage-users-preferred-language");
                if (langEl) langEl.value = user.preferred_language || "";
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
        if (banBtn) banBtn.addEventListener("click", onBan);
        if (unbanBtn) unbanBtn.addEventListener("click", onUnban);
        if (delBtn) delBtn.addEventListener("click", onDelete);
        if (prevBtn) prevBtn.addEventListener("click", function() {
            if (state.page > 1) { state.page--; fetchList(); }
        });
        if (nextBtn) nextBtn.addEventListener("click", function() {
            if (state.page < state.totalPages) { state.page++; fetchList(); }
        });

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
