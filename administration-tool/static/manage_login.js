/**
 * Management login page: submit to backend /api/v1/auth/login, store JWT in sessionStorage, redirect.
 */
(function() {
    function getApiBase() {
        var c = window.__FRONTEND_CONFIG__;
        // Prefer same-origin proxy to avoid CORS when backend is remote.
        if (c && c.apiProxyBase) return String(c.apiProxyBase).trim();
        return (c && c.backendApiUrl) ? String(c.backendApiUrl).trim() : "";
    }

    document.addEventListener("DOMContentLoaded", function() {
        var form = document.getElementById("manage-login-form");
        var submitBtn = document.getElementById("manage-login-submit");
        var errorEl = document.getElementById("manage-login-error");
        if (!form) return;

        var token = window.ManageAuth && window.ManageAuth.getToken();
        if (token) {
            window.location.href = "/manage";
            return;
        }

        form.addEventListener("submit", function(e) {
            e.preventDefault();
            if (errorEl) { errorEl.hidden = true; errorEl.textContent = ""; }
            var username = (document.getElementById("manage-login-username") || {}).value;
            var password = (document.getElementById("manage-login-password") || {}).value;
            if (!username || !password) {
                if (errorEl) { errorEl.textContent = "Username and password are required."; errorEl.hidden = false; }
                return;
            }
            if (submitBtn) submitBtn.disabled = true;

            var base = getApiBase();
            var url = (base ? base.replace(/\/$/, "") : "") + "/api/v1/auth/login";
            fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json", "Accept": "application/json" },
                body: JSON.stringify({ username: username, password: password }),
            })
                .then(function(res) {
                    return res.json().then(function(data) {
                        if (res.ok) {
                            if (data.access_token) {
                                window.ManageAuth.setToken(data.access_token);
                                if (data.user) window.ManageAuth.setStoredUser(data.user);
                            }
                            var params = new URLSearchParams(window.location.search);
                            var next = params.get("next") || "/manage";
                            if (next.indexOf("/manage") !== 0) next = "/manage";
                            window.location.href = next;
                        } else {
                            if (errorEl) {
                                errorEl.textContent = (data && data.error) || "Login failed.";
                                errorEl.hidden = false;
                            }
                            if (submitBtn) submitBtn.disabled = false;
                        }
                    });
                })
                .catch(function() {
                    if (errorEl) { errorEl.textContent = "Network error. Try again."; errorEl.hidden = false; }
                    if (submitBtn) submitBtn.disabled = false;
                });
        });
    });
})();
