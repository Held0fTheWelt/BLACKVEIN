/**
 * World Engine console: admin proxy /api/v1/admin/world-engine/* with hierarchical features.
 */
(function() {
    var pollTimer = null;

    function showBanner(msg) {
        var el = document.getElementById("wec-banner");
        if (!el) return;
        if (!msg) {
            el.style.display = "none";
            el.textContent = "";
            return;
        }
        el.style.display = "";
        el.textContent = msg;
    }

    function capsFromUser(user) {
        var a = (user && user.allowed_features) || [];
        function has(fid) { return a.indexOf(fid) >= 0; }
        var author = has("manage.world_engine_author");
        var operate = author || has("manage.world_engine_operate");
        var observe = operate || has("manage.world_engine_observe");
        return { observe: observe, operate: operate, author: author, raw: a };
    }

    function renderCaps(caps) {
        var el = document.getElementById("wec-caps");
        if (!el) return;
        var parts = [];
        if (caps.observe) parts.push("observe");
        if (caps.operate) parts.push("operate");
        if (caps.author) parts.push("author");
        el.textContent = parts.length ? ("Effective: " + parts.join(" → ")) : "No World Engine features on this account.";
    }

    function setRunActionsVisible(v) {
        var row = document.getElementById("wec-run-actions");
        if (row) row.style.display = v ? "" : "none";
    }

    function setStoryForms(caps) {
        var turnForm = document.getElementById("wec-turn-form");
        var createForm = document.getElementById("wec-create-session-form");
        if (turnForm) turnForm.style.display = caps.author ? "" : "none";
        if (createForm) createForm.style.display = caps.author ? "" : "none";
    }

    var selectedRunId = null;
    var selectedSessionId = null;

    function fetchJSON(path, opts) {
        return window.ManageAuth.apiFetchWithAuth(path, opts || {});
    }

    function loadReady() {
        return fetchJSON("/api/v1/admin/world-engine/health").then(function(data) {
            var pre = document.getElementById("wec-ready");
            if (pre) pre.textContent = JSON.stringify(data, null, 2);
            showBanner("");
        });
    }

    function loadRuns() {
        return fetchJSON("/api/v1/admin/world-engine/runs").then(function(data) {
            var host = document.getElementById("wec-runs");
            if (!host) return;
            host.innerHTML = "";
            var items = data.items || [];
            if (!items.length) {
                host.textContent = "No active runs.";
                return;
            }
            items.forEach(function(run) {
                var id = run.id || run.run_id || JSON.stringify(run);
                var btn = document.createElement("button");
                btn.type = "button";
                btn.className = "btn btn-sm";
                btn.style.display = "block";
                btn.style.marginBottom = "0.35rem";
                btn.textContent = typeof id === "string" ? id : "run";
                btn.addEventListener("click", function() {
                    selectedRunId = typeof id === "string" ? id : null;
                    loadRunDetail();
                });
                host.appendChild(btn);
            });
        });
    }

    function loadSessions() {
        return fetchJSON("/api/v1/admin/world-engine/story/sessions").then(function(data) {
            var host = document.getElementById("wec-sessions");
            if (!host) return;
            host.innerHTML = "";
            var items = data.items || [];
            if (!items.length) {
                host.textContent = "No story sessions.";
                return;
            }
            items.forEach(function(row) {
                var sid = row.session_id;
                var btn = document.createElement("button");
                btn.type = "button";
                btn.className = "btn btn-sm";
                btn.style.display = "block";
                btn.style.marginBottom = "0.35rem";
                btn.textContent = sid + " · " + (row.module_id || "") + " · turn " + String(row.turn_counter);
                btn.addEventListener("click", function() {
                    selectedSessionId = sid;
                    loadStoryDetail();
                });
                host.appendChild(btn);
            });
        });
    }

    function loadRunDetail() {
        var pre = document.getElementById("wec-run-detail");
        if (!selectedRunId) {
            if (pre) pre.textContent = "Select a run.";
            setRunActionsVisible(false);
            return;
        }
        return fetchJSON("/api/v1/admin/world-engine/runs/" + encodeURIComponent(selectedRunId))
            .then(function(data) {
                if (pre) pre.textContent = JSON.stringify(data, null, 2);
                var user = window.ManageAuth.getStoredUser();
                var caps = capsFromUser(user);
                setRunActionsVisible(caps.operate);
            })
            .catch(function(err) {
                if (pre) pre.textContent = err.message || String(err);
            });
    }

    function loadStoryDetail() {
        var st = document.getElementById("wec-story-state");
        var dg = document.getElementById("wec-story-diag");
        if (!selectedSessionId) {
            if (st) st.textContent = "Select a story session.";
            if (dg) dg.textContent = "";
            return;
        }
        return Promise.all([
            fetchJSON("/api/v1/admin/world-engine/story/sessions/" + encodeURIComponent(selectedSessionId) + "/state"),
            fetchJSON("/api/v1/admin/world-engine/story/sessions/" + encodeURIComponent(selectedSessionId) + "/diagnostics"),
        ]).then(function(pair) {
            if (st) st.textContent = JSON.stringify(pair[0], null, 2);
            var di = pair[1].diagnostics;
            if (dg) dg.textContent = JSON.stringify(di ? di.slice(-3) : [], null, 2);
        }).catch(function(err) {
            if (st) st.textContent = err.message || String(err);
        });
    }

    function refreshAll() {
        showBanner("");
        return loadReady()
            .then(loadRuns)
            .then(loadSessions)
            .catch(function(err) {
                showBanner(err.message || String(err));
            });
    }

    function setupPoll() {
        var cb = document.getElementById("wec-poll");
        if (!cb) return;
        cb.addEventListener("change", function() {
            if (pollTimer) {
                clearInterval(pollTimer);
                pollTimer = null;
            }
            if (cb.checked) {
                pollTimer = setInterval(function() { refreshAll(); }, 5000);
            }
        });
    }

    document.addEventListener("DOMContentLoaded", function() {
        if (!window.ManageAuth) return;
        window.ManageAuth.ensureAuth().then(function(user) {
            window.ManageAuth.updateUI(user);
            var caps = capsFromUser(user);
            renderCaps(caps);
            setStoryForms(caps);
            if (!caps.observe) {
                showBanner("You need at least manage.world_engine_observe (or higher) to use this console.");
                return;
            }
            return refreshAll();
        }).catch(function() {});

        var ref = document.getElementById("wec-refresh");
        if (ref) ref.addEventListener("click", function() { refreshAll(); });

        setupPoll();

        var term = document.getElementById("wec-terminate-run");
        if (term) term.addEventListener("click", function() {
            if (!selectedRunId) return;
            if (!window.confirm("Terminate run " + selectedRunId + "?")) return;
            fetchJSON("/api/v1/admin/world-engine/runs/" + encodeURIComponent(selectedRunId) + "/terminate", {
                method: "POST",
                body: JSON.stringify({ actor_display_name: "admin_console", reason: "world_engine_console" }),
            }).then(function() {
                selectedRunId = null;
                return refreshAll();
            }).catch(function(err) {
                showBanner(err.message || String(err));
            });
        });

        var turnForm = document.getElementById("wec-turn-form");
        if (turnForm) turnForm.addEventListener("submit", function(ev) {
            ev.preventDefault();
            if (!selectedSessionId) return;
            var ta = document.getElementById("wec-turn-input");
            var text = ta && ta.value ? ta.value.trim() : "";
            if (!text) return;
            fetchJSON("/api/v1/admin/world-engine/story/sessions/" + encodeURIComponent(selectedSessionId) + "/turns", {
                method: "POST",
                body: JSON.stringify({ player_input: text }),
            }).then(function() {
                if (ta) ta.value = "";
                return loadStoryDetail().then(loadSessions);
            }).catch(function(err) {
                showBanner(err.message || String(err));
            });
        });

        var createForm = document.getElementById("wec-create-session-form");
        if (createForm) createForm.addEventListener("submit", function(ev) {
            ev.preventDefault();
            var mid = document.getElementById("wec-new-module");
            var sc = document.getElementById("wec-new-scene");
            var moduleId = mid && mid.value ? mid.value.trim() : "";
            var scene = sc && sc.value ? sc.value.trim() : "scene_1";
            if (!moduleId) return;
            fetchJSON("/api/v1/admin/world-engine/story/sessions", {
                method: "POST",
                body: JSON.stringify({
                    module_id: moduleId,
                    runtime_projection: { start_scene_id: scene, scenes: [] },
                }),
            }).then(function(data) {
                selectedSessionId = data.session_id;
                return loadStoryDetail().then(loadSessions);
            }).catch(function(err) {
                showBanner(err.message || String(err));
            });
        });
    });
})();
