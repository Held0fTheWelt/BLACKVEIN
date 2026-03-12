/**
 * Management area auth: JWT in sessionStorage, authenticated fetch, /auth/me bootstrap, redirect on 401.
 */
(function() {
    var TOKEN_KEY = "wos_manage_token";
    var USER_KEY = "wos_manage_user";

    function getApiBase() {
        var c = window.__FRONTEND_CONFIG__;
        return (c && c.backendApiUrl) ? String(c.backendApiUrl).trim() : "";
    }

    function getToken() {
        try {
            return sessionStorage.getItem(TOKEN_KEY);
        } catch (e) {
            return null;
        }
    }

    function setToken(token) {
        try {
            sessionStorage.setItem(TOKEN_KEY, token);
        } catch (e) {}
    }

    function clearToken() {
        try {
            sessionStorage.removeItem(TOKEN_KEY);
            sessionStorage.removeItem(USER_KEY);
        } catch (e) {}
    }

    function setStoredUser(user) {
        try {
            sessionStorage.setItem(USER_KEY, JSON.stringify(user || {}));
        } catch (e) {}
    }

    function getStoredUser() {
        try {
            var raw = sessionStorage.getItem(USER_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            return null;
        }
    }

    /**
     * Fetch with Authorization: Bearer <token>. Returns Promise that resolves to parsed JSON
     * or rejects with { status: number, message: string }. On 401, clears token and redirects to /manage/login.
     */
    function apiFetchWithAuth(pathOrUrl, opts) {
        opts = opts || {};
        var base = getApiBase();
        var url = (pathOrUrl.indexOf("http") === 0)
            ? pathOrUrl
            : (base ? base.replace(/\/$/, "") + (pathOrUrl.indexOf("/") === 0 ? pathOrUrl : "/" + pathOrUrl) : pathOrUrl);
        var method = (opts.method || "GET").toUpperCase();
        var headers = opts.headers || {};
        headers["Accept"] = headers["Accept"] || "application/json";
        if (method === "POST" || method === "PUT" || method === "PATCH") {
            headers["Content-Type"] = headers["Content-Type"] || "application/json";
        }
        var token = getToken();
        if (token) headers["Authorization"] = "Bearer " + token;

        return new Promise(function(resolve, reject) {
            fetch(url, { method: method, headers: headers, body: opts.body })
                .then(function(res) {
                    if (res.status === 401) {
                        clearToken();
                        window.location.href = "/manage/login?next=" + encodeURIComponent(window.location.pathname);
                        reject({ status: 401, message: "Unauthorized" });
                        return;
                    }
                    var next = res.ok
                        ? res.json().then(function(data) { resolve(data); }).catch(function() { reject({ status: res.status, message: "Invalid response" }); })
                        : res.json().catch(function() { return {}; }).then(function(body) {
                            var msg = (body && body.error) ? body.error : "Request failed: " + res.status;
                            reject({ status: res.status, message: msg });
                        });
                    return next;
                })
                .catch(function(err) {
                    if (err && err.status) return;
                    reject({ status: 0, message: (err && err.message) || "Network error" });
                });
        });
    }

    /**
     * Load current user from /api/v1/auth/me. Returns Promise<user> or rejects. Updates stored user on success.
     */
    function getMe() {
        return apiFetchWithAuth("/api/v1/auth/me").then(function(user) {
            setStoredUser(user);
            return user;
        });
    }

    /**
     * Ensure user is logged in: if no token, redirect to login. Otherwise call getMe() and return user.
     * On 401/403 getMe redirects. Use on every manage page except login.
     */
    function ensureAuth() {
        if (!getToken()) {
            window.location.href = "/manage/login?next=" + encodeURIComponent(window.location.pathname);
            return Promise.reject();
        }
        return getMe();
    }

    /**
     * Show current user and role in #manage-user-info; hide Users nav if not admin.
     */
    function updateUI(user) {
        var infoEl = document.getElementById("manage-user-info");
        if (infoEl && user) {
            infoEl.textContent = (user.username || "") + (user.role ? " (" + user.role + ")" : "");
        }
        var allowed = user && user.allowed_features ? user.allowed_features : [];
        var hasFeature = function(fid) { return allowed.indexOf(fid) >= 0; };
        [].forEach.call(document.querySelectorAll(".manage-nav-link[data-feature]"), function(link) {
            var fid = link.getAttribute("data-feature");
            link.style.display = fid && hasFeature(fid) ? "" : "none";
        });
        var usersCard = document.getElementById("manage-dashboard-users");
        if (usersCard) usersCard.style.display = hasFeature("manage.users") ? "" : "none";
    }

    /**
     * Logout: clear token and redirect to manage login.
     */
    function logout() {
        clearToken();
        window.location.href = "/manage/login";
    }

    document.addEventListener("DOMContentLoaded", function() {
        var logoutBtn = document.getElementById("manage-logout");
        if (logoutBtn) logoutBtn.addEventListener("click", logout);

        var path = window.location.pathname || "";
        if (path.indexOf("/manage") === 0 && path !== "/manage/login" && path !== "/manage/login/") {
            if (!getToken()) {
                window.location.href = "/manage/login?next=" + encodeURIComponent(path);
                return;
            }
            getMe().then(updateUI).catch(function() {});
        }
    });

    window.ManageAuth = {
        getToken: getToken,
        setToken: setToken,
        clearToken: clearToken,
        apiFetchWithAuth: apiFetchWithAuth,
        getMe: getMe,
        ensureAuth: ensureAuth,
        updateUI: updateUI,
        getStoredUser: getStoredUser,
        setStoredUser: setStoredUser,
        logout: logout,
    };
})();
