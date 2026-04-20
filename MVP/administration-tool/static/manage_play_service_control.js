/**
 * Play-Service control: GET/POST /api/v1/admin/play-service-control (+ /test, /apply) via proxy.
 */
(function() {
    function showBanner(kind, msg) {
        var errEl = document.getElementById("manage-psc-banner");
        var okEl = document.getElementById("manage-psc-success");
        if (errEl) {
            errEl.style.display = "none";
            errEl.textContent = "";
        }
        if (okEl) {
            okEl.style.display = "none";
            okEl.textContent = "";
        }
        if (!msg) return;
        if (kind === "ok" && okEl) {
            okEl.style.display = "";
            okEl.textContent = msg;
        } else if (errEl) {
            errEl.style.display = "";
            errEl.textContent = msg;
        }
    }

    function presenceLabel(v) {
        return v ? "present (environment)" : "not set";
    }

    function fillForm(d) {
        if (!d) return;
        var mode = document.getElementById("manage-psc-mode");
        var en = document.getElementById("manage-psc-enabled");
        var pub = document.getElementById("manage-psc-public-url");
        var inn = document.getElementById("manage-psc-internal-url");
        var to = document.getElementById("manage-psc-timeout-ms");
        var al = document.getElementById("manage-psc-allow-new");
        if (mode) mode.value = d.mode || "disabled";
        if (en) en.checked = !!d.enabled;
        if (pub) pub.value = d.public_url || "";
        if (inn) inn.value = d.internal_url || "";
        if (to) to.value = d.request_timeout_ms != null ? String(d.request_timeout_ms) : "30000";
        if (al) al.checked = d.allow_new_sessions !== false;
        var sp = document.getElementById("manage-psc-secret-present");
        var kp = document.getElementById("manage-psc-key-present");
        if (sp) sp.textContent = presenceLabel(d.shared_secret_present);
        if (kp) kp.textContent = presenceLabel(d.internal_api_key_present);
    }

    function renderObserved(data) {
        var el = document.getElementById("manage-psc-observed");
        if (!el || !data) return;
        var o = data.observed_state || {};
        var lines = [
            "Status text (not color-only):",
            "effective_mode: " + (o.effective_mode || "—"),
            "effective_enabled: " + String(!!o.effective_enabled),
            "config_complete: " + String(!!o.config_complete),
            "health: " + (o.health || "—"),
            "readiness: " + (o.readiness || "—"),
            "allow_new_sessions_effective: " + String(!!o.allow_new_sessions_effective),
            "shared_secret_present: " + String(!!o.shared_secret_present),
            "internal_api_key_present: " + String(!!o.internal_api_key_present),
            "generated_at: " + (data.generated_at || "—")
        ];
        el.innerHTML = "<pre class=\"manage-psc-json\">" + lines.join("\n") + "</pre>";
        var lt = document.getElementById("manage-psc-last-test");
        var la = document.getElementById("manage-psc-last-apply");
        if (lt) lt.textContent = data.last_test_result ? JSON.stringify(data.last_test_result, null, 2) : "—";
        if (la) la.textContent = data.last_apply_result ? JSON.stringify(data.last_apply_result, null, 2) : "—";
    }

    function payloadFromForm() {
        var mode = (document.getElementById("manage-psc-mode") || {}).value || "disabled";
        var enabled = !!(document.getElementById("manage-psc-enabled") || {}).checked;
        var public_url = (document.getElementById("manage-psc-public-url") || {}).value || "";
        var internal_url = (document.getElementById("manage-psc-internal-url") || {}).value || "";
        var rawTo = (document.getElementById("manage-psc-timeout-ms") || {}).value || "30000";
        var request_timeout_ms = parseInt(rawTo, 10);
        if (isNaN(request_timeout_ms)) request_timeout_ms = 30000;
        var allow_new_sessions = !!(document.getElementById("manage-psc-allow-new") || {}).checked;
        return {
            mode: mode,
            enabled: enabled,
            public_url: public_url.trim(),
            internal_url: internal_url.trim(),
            request_timeout_ms: request_timeout_ms,
            allow_new_sessions: allow_new_sessions
        };
    }

    function loadAll() {
        showBanner(null, "");
        return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/play-service-control").then(function(data) {
            fillForm(data.desired_state || {});
            renderObserved(data);
        });
    }

    document.addEventListener("DOMContentLoaded", function() {
        if (!window.ManageAuth) return;
        window.ManageAuth.ensureAuth()
            .then(function() {
                return loadAll();
            })
            .catch(function(e) {
                showBanner("err", (e && e.message) || "Failed to load control state");
            });

        var form = document.getElementById("manage-psc-form");
        if (form) {
            form.addEventListener("submit", function(ev) {
                ev.preventDefault();
                showBanner(null, "");
                var body = JSON.stringify(payloadFromForm());
                window.ManageAuth.apiFetchWithAuth("/api/v1/admin/play-service-control", { method: "POST", body: body })
                    .then(function(res) {
                        if (!res.saved) {
                            var errs = (res.validation_errors || []).join("; ");
                            showBanner("err", errs || "Validation failed");
                            return;
                        }
                        showBanner("ok", "Desired state saved.");
                        fillForm(res.desired_state || {});
                    })
                    .catch(function(e) {
                        showBanner("err", (e && e.message) || "Save failed");
                    });
            });
        }

        function postAction(path, okMsg) {
            showBanner(null, "");
            window.ManageAuth.apiFetchWithAuth(path, { method: "POST", body: "{}" })
                .then(function(res) {
                    if (path.indexOf("/apply") >= 0) {
                        if (!res.ok) {
                            var m = (res.result && res.result.message) || "Apply failed";
                            if (res.result && res.result.validation_errors)
                                m += " — " + res.result.validation_errors.join("; ");
                            showBanner("err", m);
                        } else {
                            showBanner("ok", okMsg || "Apply completed.");
                        }
                    } else if (path.indexOf("/test") >= 0) {
                        if (!res.ok) {
                            showBanner("err", "Test reported failure; see Last test below.");
                        } else {
                            showBanner("ok", okMsg || "Test finished.");
                        }
                    } else if (okMsg) {
                        showBanner("ok", okMsg);
                    }
                    return loadAll();
                })
                .catch(function(e) {
                    showBanner("err", (e && e.message) || "Request failed");
                });
        }

        var btnTest = document.getElementById("manage-psc-test");
        if (btnTest) btnTest.addEventListener("click", function() {
            postAction("/api/v1/admin/play-service-control/test", "Test finished (see Last test).");
        });
        var btnApply = document.getElementById("manage-psc-apply");
        if (btnApply) btnApply.addEventListener("click", function() {
            postAction("/api/v1/admin/play-service-control/apply", "Apply completed.");
        });
        var btnRef = document.getElementById("manage-psc-refresh");
        if (btnRef) btnRef.addEventListener("click", function() {
            loadAll().catch(function(e) {
                showBanner("err", (e && e.message) || "Refresh failed");
            });
        });
    });
})();
