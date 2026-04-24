/**
 * System diagnosis: GET /api/v1/admin/system-diagnosis via same-origin proxy.
 */
(function() {
    var REFRESH_MS = 15000;

    function statusBadgeClass(status) {
        if (status === "fail") return "manage-dx-badge manage-dx-badge--fail";
        if (status === "initialized") return "manage-dx-badge manage-dx-badge--init";
        return "manage-dx-badge manage-dx-badge--ok";
    }

    function escapeHtml(s) {
        if (s == null) return "";
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function renderMeta(data) {
        var el = document.getElementById("manage-diagnosis-meta");
        if (!el) return;
        var parts = [];
        if (data.generated_at) {
            parts.push("<strong>Generated:</strong> " + escapeHtml(data.generated_at));
        }
        if (data.cached) {
            parts.push("<strong>Cache:</strong> served from " + (data.cache && data.cache.hit ? "TTL cache" : "fresh"));
            if (typeof data.stale_seconds === "number") {
                parts.push("<strong>Age:</strong> " + data.stale_seconds + " s since snapshot");
            }
        } else {
            parts.push("<strong>Cache:</strong> fresh run");
        }
        el.innerHTML = "<p class=\"manage-state\">" + parts.join(" · ") + "</p>";
    }

    function renderOverall(data) {
        var el = document.getElementById("manage-diagnosis-overall");
        if (!el) return;
        var st = data.overall_status || "initialized";
        var sum = data.summary || {};
        el.innerHTML =
            "<header class=\"panel-header\"><h2>Overall</h2></header>" +
            "<div class=\"manage-dx-overall-inner\">" +
            "<span class=\"" + statusBadgeClass(st) + "\" title=\"Overall status\">" + escapeHtml(st) + "</span>" +
            "<span class=\"manage-dx-summary-counts\" aria-label=\"Summary counts\">" +
            "running: " + (sum.running || 0) +
            " · initialized: " + (sum.initialized || 0) +
            " · fail: " + (sum.fail || 0) +
            "</span></div>";
    }

    function renderCheckDetails(c) {
        var html = "";
        if (c.details && typeof c.details === "object") {
            html += "<details class=\"manage-dx-check-details\">";
            html += "<summary class=\"muted\">Details</summary>";
            html += "<pre class=\"manage-dx-details-json muted\">" + escapeHtml(JSON.stringify(c.details, null, 2)) + "</pre>";
            html += "</details>";
        }
        return html;
    }

    function renderGateLink(c) {
        var html = "";
        if (c.gate_id) {
            var gateBadgeClass = "manage-dx-gate-badge";
            var gateStatus = c.gate_status || "unknown";
            if (gateStatus === "closed") gateBadgeClass += " manage-dx-gate-badge--closed";
            else if (gateStatus === "partial") gateBadgeClass += " manage-dx-gate-badge--partial";
            else if (gateStatus === "open") gateBadgeClass += " manage-dx-gate-badge--open";

            html += "<p class=\"manage-dx-gate-info\">";
            html += "Readiness gate: <strong>" + escapeHtml(c.gate_id) + "</strong>";
            html += " <span class=\"" + gateBadgeClass + "\">" + escapeHtml(gateStatus) + "</span>";
            html += " <a href=\"/manage/ai-stack/release-readiness\" class=\"manage-dx-gate-link\">View all gates →</a>";
            html += "</p>";
        }
        return html;
    }

    function renderGroups(data) {
        var root = document.getElementById("manage-diagnosis-groups");
        if (!root) return;
        var groups = data.groups || [];
        var html = "";

        // Show partial gate count if available
        if (typeof data.partial_gate_count === "number") {
            html += "<section class=\"panel manage-dx-gates-summary\">";
            html += "<header class=\"panel-header\"><h2>Readiness Status</h2></header>";
            html += "<p class=\"muted\" style=\"margin:0;\">Partial gates: <strong>" + data.partial_gate_count + "</strong>";
            if (data.partial_gate_count > 0) {
                html += " <a href=\"/manage/ai-stack/release-readiness?status=partial\">View partial gates →</a>";
            }
            html += "</p>";
            html += "</section>";
        }

        for (var g = 0; g < groups.length; g++) {
            var grp = groups[g];
            html += "<section class=\"panel manage-dx-group\">";
            html += "<header class=\"panel-header\"><h2>" + escapeHtml(grp.label || grp.id) + "</h2></header>";
            html += "<ul class=\"manage-dx-check-list\">";
            var checks = grp.checks || [];
            for (var i = 0; i < checks.length; i++) {
                var c = checks[i];
                var crit = c.critical ? " · critical" : "";
                html += "<li class=\"manage-dx-check\">";
                html += "<div class=\"manage-dx-check-head\">";
                html += "<span class=\"" + statusBadgeClass(c.status) + "\">" + escapeHtml(c.status) + "</span>";
                html += "<strong class=\"manage-dx-check-label\">" + escapeHtml(c.label || c.id) + "</strong>";
                html += "<span class=\"muted\">" + escapeHtml(crit) + "</span>";
                html += "</div>";
                html += "<p class=\"manage-dx-msg\">" + escapeHtml(c.message || "") + "</p>";
                if (typeof c.latency_ms === "number") {
                    html += "<p class=\"manage-dx-detail muted\">Latency: " + c.latency_ms + " ms";
                    if (c.timed_out) html += " · timed out";
                    html += "</p>";
                }
                if (c.source) {
                    html += "<p class=\"manage-dx-detail muted\">Source: " + escapeHtml(c.source) + "</p>";
                }
                // Add gate information
                html += renderGateLink(c);
                // Add expandable details
                html += renderCheckDetails(c);
                html += "</li>";
            }
            html += "</ul></section>";
        }
        root.innerHTML = html;
    }

    function loadDiagnosis(refresh) {
        var errEl = document.getElementById("manage-diagnosis-error");
        if (errEl) {
            errEl.style.display = "none";
            errEl.textContent = "";
        }
        var path = "/api/v1/admin/system-diagnosis";
        if (refresh) path += "?refresh=1";
        return window.ManageAuth.apiFetchWithAuth(path).then(function(data) {
            renderMeta(data);
            renderOverall(data);
            renderGroups(data);
        });
    }

    function showError(msg) {
        var errEl = document.getElementById("manage-diagnosis-error");
        if (!errEl) return;
        errEl.style.display = "";
        errEl.textContent = msg || "Request failed";
    }

    document.addEventListener("DOMContentLoaded", function() {
        if (!window.ManageAuth) return;
        var timer = null;
        function schedule() {
            if (timer) clearInterval(timer);
            timer = setInterval(function() {
                loadDiagnosis(false).catch(function(e) {
                    showError(e && e.message ? e.message : "Auto-refresh failed");
                });
            }, REFRESH_MS);
        }
        window.ManageAuth.ensureAuth()
            .then(function() {
                return loadDiagnosis(false);
            })
            .then(function() {
                schedule();
            })
            .catch(function() {});

        var btn = document.getElementById("manage-diagnosis-refresh");
        if (btn) {
            btn.addEventListener("click", function() {
                loadDiagnosis(true).catch(function(e) {
                    showError(e && e.message ? e.message : "Refresh failed");
                });
            });
        }
    });
})();
