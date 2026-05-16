/**
 * Runtime Configuration Truth — configured vs. effective vs. loaded.
 *
 * Shows what's in the database, what's effective, what's loaded in runtime,
 * and network connectivity state.
 */
(function() {
    function apiData(res) {
        if (res && res.data !== undefined && Object.prototype.hasOwnProperty.call(res, "ok")) {
            return res.data || {};
        }
        return res || {};
    }

    function escapeHtml(s) {
        if (s == null) return "";
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function statusBadgeClass(status) {
        var base = "config-truth-status-badge";
        if (status === "configured") return base + " configured";
        if (status === "loaded") return base + " loaded";
        if (status === "error") return base + " error";
        if (status === "requires_http_probe") return base + " requires-probe";
        return base;
    }

    function renderField(label, value) {
        var displayValue = value;
        if (typeof value === "object") {
            displayValue = JSON.stringify(value, null, 2);
        } else if (value === null || value === undefined) {
            displayValue = "(not set)";
        }
        return (
            "<div class=\"config-truth-field\">" +
            "<div class=\"config-truth-field-label\">" + escapeHtml(label) + "</div>" +
            "<div class=\"config-truth-field-value\">" + escapeHtml(String(displayValue)) + "</div>" +
            "</div>"
        );
    }

    function renderSection(data) {
        var html = "";
        if (!data) return html;

        if (data.status) {
            html += renderField("Status", data.status) + " ";
            if (data.message) {
                html += renderField("Message", data.message) + " ";
            }
        }

        if (data.backend_configured !== undefined) {
            html += renderField("Backend Configured", data.backend_configured ? "yes" : "no") + " ";
        }

        if (data.bootstrap_state) {
            html += renderField("Bootstrap State", data.bootstrap_state) + " ";
        }

        if (data.runtime_profile) {
            html += renderField("Runtime Profile", data.runtime_profile) + " ";
        }

        if (data.generation_execution_mode) {
            html += renderField("Generation Mode", data.generation_execution_mode) + " ";
        }

        if (data.retrieval_execution_mode) {
            html += renderField("Retrieval Mode", data.retrieval_execution_mode) + " ";
        }

        if (data.validation_execution_mode) {
            html += renderField("Validation Mode", data.validation_execution_mode) + " ";
        }

        if (data.provider_selection_mode) {
            html += renderField("Provider Selection", data.provider_selection_mode) + " ";
        }

        if (data.bootstrap_completed_at) {
            html += renderField("Bootstrap Completed", data.bootstrap_completed_at) + " ";
        }

        if (data.resolved_at) {
            html += renderField("Resolved At", data.resolved_at) + " ";
        }

        if (data.backend_effective !== undefined) {
            html += renderField("Backend Effective", data.backend_effective ? "yes" : "no") + " ";
        }

        if (data.world_engine_loaded !== undefined) {
            html += renderField("World-Engine Loaded", data.world_engine_loaded === null ? "unknown" : (data.world_engine_loaded ? "yes" : "no")) + " ";
        }

        if (data.play_service_reachable !== undefined) {
            html += renderField("Play-Service Reachable", data.play_service_reachable === null ? "unknown" : (data.play_service_reachable ? "yes" : "no")) + " ";
        }

        if (data.check_endpoint) {
            html += renderField("Check Endpoint", data.check_endpoint) + " ";
        }

        return html;
    }

    function renderSummary(summary) {
        if (!summary) return "";

        var statusClass = "ready";
        if (summary.status === "partial") statusClass = "partial";
        if (summary.status === "degraded") statusClass = "degraded";

        var html = (
            "<div class=\"config-truth-status-card " + statusClass + "\">" +
            "<div class=\"config-truth-status-label\">Status</div>" +
            "<div class=\"config-truth-status-value\">" + escapeHtml(summary.status) + "</div>" +
            "</div>"
        );

        if (summary.issues && summary.issues.length > 0) {
            html += (
                "<div style=\"grid-column: 1 / -1;\">" +
                "<p class=\"muted\" style=\"margin: 0;\"><strong>Issues:</strong></p>" +
                "<ul class=\"config-truth-issues\">"
            );
            for (var i = 0; i < summary.issues.length; i++) {
                html += "<li>" + escapeHtml(summary.issues[i]) + "</li>";
            }
            html += "</ul></div>";
        }

        return html;
    }

    function loadTruth() {
        var btn = document.getElementById("config-truth-refresh");
        if (btn) btn.disabled = true;

        if (!window.ManageAuth || typeof window.ManageAuth.apiFetchWithAuth !== "function") {
            showMessage("ManageAuth API bridge unavailable", true);
            if (btn) btn.disabled = false;
            return;
        }

        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/runtime/config-truth")
            .then(function(resp) {
                var data = apiData(resp);
                if (!data || typeof data !== "object") {
                    throw new Error("No data returned");
                }

                // Render summary
                var summaryEl = document.getElementById("config-truth-summary-content");
                if (summaryEl) {
                    summaryEl.innerHTML = renderSummary(data.summary);
                }

                // Render sections
                var configEl = document.getElementById("config-truth-configured");
                if (configEl) configEl.innerHTML = renderSection(data.backend_configured);

                var effectiveEl = document.getElementById("config-truth-effective");
                if (effectiveEl) effectiveEl.innerHTML = renderSection(data.backend_effective);

                var worldEngineEl = document.getElementById("config-truth-world-engine");
                if (worldEngineEl) worldEngineEl.innerHTML = renderSection(data.world_engine_state);

                var playServiceEl = document.getElementById("config-truth-play-service");
                if (playServiceEl) playServiceEl.innerHTML = renderSection(data.play_service_connectivity);

                // Render raw JSON
                var jsonEl = document.getElementById("config-truth-json");
                if (jsonEl) {
                    jsonEl.textContent = JSON.stringify(data, null, 2);
                }

                showMessage("Config truth loaded", false);
            })
            .catch(function(err) {
                showMessage("Failed to load config truth: " + err.message, true);
            })
            .finally(function() {
                if (btn) btn.disabled = false;
            });
    }

    function showMessage(msg, isError) {
        var errorEl = document.getElementById("config-truth-error");
        var successEl = document.getElementById("config-truth-success");
        if (errorEl) {
            errorEl.hidden = true;
            errorEl.style.display = "none";
            errorEl.textContent = "";
        }
        if (successEl) {
            successEl.hidden = true;
            successEl.style.display = "none";
            successEl.textContent = "";
        }
        if (isError) {
            if (errorEl) {
                errorEl.textContent = msg;
                errorEl.hidden = false;
                errorEl.style.display = "";
            }
            return;
        }
        if (successEl) {
            successEl.textContent = msg;
            successEl.hidden = false;
            successEl.style.display = "";
        }
    }

    document.addEventListener("DOMContentLoaded", function() {
        if (!window.ManageAuth || typeof window.ManageAuth.ensureAuth !== "function") {
            showMessage("ManageAuth unavailable", true);
            return;
        }
        var btn = document.getElementById("config-truth-refresh");
        if (btn) {
            btn.addEventListener("click", loadTruth);
        }
        window.ManageAuth.ensureAuth()
            .then(loadTruth)
            .catch(function(err) {
                showMessage("Authentication check failed: " + (err && err.message ? err.message : "unauthorized"), true);
            });
    });
})();
