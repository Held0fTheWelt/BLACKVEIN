/**
 * MCP Operations cockpit: admin APIs via same-origin proxy + ManageAuth.
 */
(function() {
    function showBanner(kind, msg) {
        var errEl = document.getElementById("mcp-ops-banner");
        var okEl = document.getElementById("mcp-ops-success");
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

    function esc(s) {
        if (s == null || s === "") return "";
        var d = document.createElement("div");
        d.textContent = String(s);
        return d.innerHTML;
    }

    var currentTab = "overview";

    function setTab(name) {
        currentTab = name;
        var tabs = document.querySelectorAll(".mcp-ops-tab");
        var panels = document.querySelectorAll(".mcp-ops-panel");
        tabs.forEach(function(t) {
            var on = t.getAttribute("data-tab") === name;
            t.classList.toggle("is-active", on);
            t.setAttribute("aria-selected", on ? "true" : "false");
        });
        panels.forEach(function(p) {
            var id = p.id.replace("mcp-panel-", "");
            var on = id === name;
            p.style.display = on ? "" : "none";
            p.hidden = !on;
        });
        if (window.location.hash !== "#" + name) {
            history.replaceState(null, "", "#" + name);
        }
    }

    function loadOverview() {
        return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/mcp/overview").then(function(d) {
            var el = document.getElementById("mcp-ops-overview");
            if (!el) return;
            var lines = [];
            lines.push("<p><strong>Retention (telemetry)</strong>: " + esc(d.retention_days) + " days</p>");
            lines.push("<p><strong>Open diagnostic cases</strong>: " + esc(d.open_diagnostic_cases) + "</p>");
            var l24 = d.last_24h || {};
            lines.push("<p><strong>Last 24h</strong>: telemetry rows " + esc(l24.telemetry_rows) + ", errors " + esc(l24.error_or_code_rows) + "</p>");
            lines.push("<h2>Suites (registry)</h2>");
            lines.push("<table><thead><tr><th>Suite</th><th>Tools</th><th>Resources</th><th>Prompts</th></tr></thead><tbody>");
            (d.suites || []).forEach(function(s) {
                lines.push("<tr><td>" + esc(s.suite_name) + "</td><td>" + esc(s.tool_count) + "</td><td>" + esc(s.resource_count) + "</td><td>" + esc(s.prompt_count) + "</td></tr>");
            });
            lines.push("</tbody></table>");
            lines.push("<h2>Recent tool activity</h2>");
            lines.push("<div class=\"mcp-ops-table-wrap\"><table><thead><tr><th>Time</th><th>Suite</th><th>Tool</th><th>Outcome</th><th>trace_id</th></tr></thead><tbody>");
            (d.recent_tool_activity || []).forEach(function(r) {
                var suiteCell = r.suite_name === "unknown"
                    ? "<span class=\"mcp-ops-badge-unknown\" title=\"Suite could not be derived from canonical tool map\">Unknown suite</span>"
                    : esc(r.suite_name);
                if (r.process_suite_hint && r.process_suite_hint !== "all" && r.suite_name === "unknown") {
                    suiteCell += " <span class=\"muted\">(process: " + esc(r.process_suite_hint) + ")</span>";
                }
                lines.push("<tr><td>" + esc(r.timestamp) + "</td><td>" + suiteCell + "</td><td>" + esc(r.target_name) + "</td><td>" + esc(r.outcome_status) + "</td><td><code>" + esc(r.correlation_id) + "</code></td></tr>");
            });
            lines.push("</tbody></table></div>");
            el.innerHTML = lines.join("");
        });
    }

    function loadActivity() {
        var errOnly = !!(document.getElementById("mcp-activity-errors-only") || {}).checked;
        var q = errOnly ? "?errors_only=true&limit=100" : "?limit=100";
        return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/mcp/activity" + q).then(function(d) {
            var el = document.getElementById("mcp-ops-activity");
            if (!el) return;
            var rows = ["<table><thead><tr><th>Time</th><th>Suite</th><th>Tool</th><th>Outcome</th><th>ms</th><th>trace_id</th></tr></thead><tbody>"];
            (d.items || []).forEach(function(r) {
                rows.push("<tr><td>" + esc(r.timestamp) + "</td><td>" + esc(r.suite_name) + "</td><td>" + esc(r.target_name) + "</td><td>" + esc(r.outcome_status) + "</td><td>" + esc(r.duration_ms) + "</td><td><code>" + esc(r.correlation_id) + "</code></td></tr>");
            });
            rows.push("</tbody></table><p class=\"muted\">Total: " + esc(d.total) + "</p>");
            el.innerHTML = rows.join("");
        });
    }

    function loadDiagnostics() {
        return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/mcp/diagnostics?limit=100").then(function(d) {
            var el = document.getElementById("mcp-ops-diagnostics");
            if (!el) return;
            var rows = ["<table><thead><tr><th>case_id</th><th>Type</th><th>Severity</th><th>Status</th><th>Suite</th><th>Summary</th><th>trace</th></tr></thead><tbody>"];
            (d.items || []).forEach(function(c) {
                rows.push("<tr><td><code>" + esc(c.case_id) + "</code></td><td>" + esc(c.case_type) + "</td><td>" + esc(c.severity) + "</td><td>" + esc(c.status) + "</td><td>" + esc(c.suite_display) + "</td><td>" + esc(c.summary) + "</td><td>" + esc(c.trace_id) + "</td></tr>");
            });
            rows.push("</tbody></table><p class=\"muted\">Total: " + esc(d.total) + "</p>");
            el.innerHTML = rows.join("");
        });
    }

    function loadLogs() {
        var errOnly = !!(document.getElementById("mcp-logs-errors-only") || {}).checked;
        var q = errOnly ? "?errors_only=true&limit=100" : "?limit=100";
        return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/mcp/logs" + q).then(function(d) {
            var el = document.getElementById("mcp-ops-logs");
            if (!el) return;
            var rows = ["<table><thead><tr><th>Time</th><th>Level</th><th>Type</th><th>Method</th><th>Suite</th><th>Status</th><th>trace_id</th></tr></thead><tbody>"];
            (d.items || []).forEach(function(r) {
                rows.push("<tr><td>" + esc(r.timestamp) + "</td><td>" + esc(r.log_level) + "</td><td>" + esc(r.record_type) + "</td><td>" + esc(r.method) + "</td><td>" + esc(r.suite_name) + "</td><td>" + esc(r.status) + "</td><td><code>" + esc(r.trace_id) + "</code></td></tr>");
            });
            rows.push("</tbody></table><p class=\"muted\">Total: " + esc(d.total) + "</p>");
            el.innerHTML = rows.join("");
        });
    }

    function refreshCurrent() {
        showBanner(null, "");
        var p = Promise.resolve();
        if (currentTab === "overview") p = loadOverview();
        else if (currentTab === "activity") p = loadActivity();
        else if (currentTab === "diagnostics") p = loadDiagnostics();
        else if (currentTab === "logs") p = loadLogs();
        return p.catch(function(e) {
            showBanner("err", (e && e.message) ? e.message : "Request failed");
        });
    }

    function postAction(path, body) {
        return window.ManageAuth.apiFetchWithAuth(path, {
            method: "POST",
            body: body != null ? JSON.stringify(body) : "{}"
        });
    }

    document.addEventListener("DOMContentLoaded", function() {
        var hash = (window.location.hash || "").replace(/^#/, "");
        if (hash && ["overview", "activity", "diagnostics", "logs", "actions"].indexOf(hash) >= 0) {
            setTab(hash);
        } else {
            setTab("overview");
        }

        document.querySelectorAll(".mcp-ops-tab").forEach(function(btn) {
            btn.addEventListener("click", function() {
                var t = btn.getAttribute("data-tab");
                if (!t) return;
                setTab(t);
                refreshCurrent().catch(function() {});
            });
        });

        var refBtn = document.getElementById("mcp-ops-refresh");
        if (refBtn) refBtn.addEventListener("click", function() { refreshCurrent(); });

        var ae = document.getElementById("mcp-activity-errors-only");
        if (ae) ae.addEventListener("change", function() { loadActivity().catch(function(e) { showBanner("err", e.message || "failed"); }); });
        var le = document.getElementById("mcp-logs-errors-only");
        if (le) le.addEventListener("change", function() { loadLogs().catch(function(e) { showBanner("err", e.message || "failed"); }); });

        document.getElementById("mcp-action-refresh-catalog") && document.getElementById("mcp-action-refresh-catalog").addEventListener("click", function() {
            postAction("/api/v1/admin/mcp/actions/refresh-catalog", {}).then(function(d) {
                document.getElementById("mcp-ops-actions-output").textContent = JSON.stringify(d, null, 2);
                showBanner("ok", "Catalog alignment refreshed.");
            }).catch(function(e) { showBanner("err", e.message || "failed"); });
        });
        document.getElementById("mcp-action-rebuild") && document.getElementById("mcp-action-rebuild").addEventListener("click", function() {
            postAction("/api/v1/admin/mcp/actions/retry-job", { since_days: 30 }).then(function(d) {
                document.getElementById("mcp-ops-actions-output").textContent = JSON.stringify(d, null, 2);
                showBanner("ok", "Rebuild completed.");
            }).catch(function(e) { showBanner("err", e.message || "failed"); });
        });
        document.getElementById("mcp-action-audit-bundle") && document.getElementById("mcp-action-audit-bundle").addEventListener("click", function() {
            postAction("/api/v1/admin/mcp/actions/generate-audit-bundle", { limit_events: 500 }).then(function(d) {
                document.getElementById("mcp-ops-actions-output").textContent = JSON.stringify(d, null, 2);
                showBanner("ok", "Audit bundle generated (see below).");
            }).catch(function(e) { showBanner("err", e.message || "failed"); });
        });
        document.getElementById("mcp-action-reclassify") && document.getElementById("mcp-action-reclassify").addEventListener("click", function() {
            var cid = (document.getElementById("mcp-reclass-case-id") || {}).value || "";
            var su = (document.getElementById("mcp-reclass-suite") || {}).value;
            var st = (document.getElementById("mcp-reclass-status") || {}).value;
            var body = { case_id: cid.trim() };
            if (su && su.trim()) body.suite_display_override = su.trim();
            if (st && st.trim()) body.status = st.trim();
            postAction("/api/v1/admin/mcp/actions/reclassify-diagnostic", body).then(function(d) {
                document.getElementById("mcp-ops-actions-output").textContent = JSON.stringify(d, null, 2);
                showBanner("ok", "Case updated.");
            }).catch(function(e) { showBanner("err", e.message || "failed"); });
        });

        var mform = document.getElementById("mcp-manual-case-form");
        if (mform) {
            mform.addEventListener("submit", function(ev) {
                ev.preventDefault();
                var fd = new FormData(mform);
                var payload = {
                    case_type: (fd.get("case_type") || "").toString().trim(),
                    summary: (fd.get("summary") || "").toString().trim(),
                    suite_name: (fd.get("suite_name") || "unknown").toString().trim() || "unknown"
                };
                postAction("/api/v1/admin/mcp/diagnostics/manual", payload).then(function() {
                    showBanner("ok", "Manual case created.");
                    loadDiagnostics();
                    mform.reset();
                }).catch(function(e) { showBanner("err", e.message || "failed"); });
            });
        }

        refreshCurrent();
    });
})();
