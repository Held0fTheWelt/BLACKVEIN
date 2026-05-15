/**
 * AI Stack Release Readiness — gate dashboard (ManageAuth + diagnosis sync on refresh).
 */
(function () {
    "use strict";

    var gates = [];
    var filteredGates = [];

    function $(id) {
        return document.getElementById(id);
    }

    function escapeHtml(s) {
        if (s == null) return "";
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function apiData(res) {
        if (res && res.data !== undefined && Object.prototype.hasOwnProperty.call(res, "ok")) {
            return res.data || {};
        }
        return res || {};
    }

    function statusBadgeClass(status) {
        var base = "readiness-status-badge manage-dx-badge";
        if (status === "closed") return base + " manage-dx-badge--ok readiness-status-badge--closed";
        if (status === "partial") return base + " manage-dx-badge--init readiness-status-badge--partial";
        if (status === "open") return base + " manage-dx-badge--fail readiness-status-badge--open";
        return base;
    }

    function showBanner(msg, isError) {
        var errEl = $("readiness-banner");
        var okEl = $("readiness-success");
        if (errEl) {
            errEl.hidden = !isError;
            errEl.style.display = isError ? "" : "none";
            if (isError) errEl.textContent = msg;
        }
        if (okEl && !isError) {
            okEl.hidden = false;
            okEl.style.display = "";
            okEl.textContent = msg;
            setTimeout(function () {
                okEl.hidden = true;
                okEl.style.display = "none";
            }, 4000);
        }
        var headerResult = $("readiness-header-result");
        if (headerResult && !isError) {
            headerResult.hidden = false;
            headerResult.textContent = msg;
            setTimeout(function () {
                headerResult.hidden = true;
                headerResult.textContent = "";
            }, 4000);
        }
    }

    function applyUrlFilters() {
        var params = new URLSearchParams(window.location.search);
        var status = params.get("status");
        var statusEl = $("readiness-filter-status");
        if (status && statusEl) statusEl.value = status;
    }

    function syncGatesFromDiagnosis() {
        if (!window.ManageAuth) {
            return Promise.reject({ message: "ManageAuth is not loaded." });
        }
        return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/system-diagnosis?refresh=1");
    }

    function fetchGates() {
        if (!window.ManageAuth) {
            return Promise.reject({ message: "ManageAuth is not loaded." });
        }
        return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai-stack/release-readiness/gates").then(apiData);
    }

    function loadGates(runDiagnosisSync) {
        var btn = $("readiness-refresh-btn");
        if (btn) btn.disabled = true;

        var chain = runDiagnosisSync ? syncGatesFromDiagnosis() : Promise.resolve();

        return chain
            .then(fetchGates)
            .then(function (data) {
                gates = data.gates || [];
                renderSummary(data.summary);
                applyFilters();
                showBanner(
                    runDiagnosisSync
                        ? "Gates synced from system diagnosis (" + gates.length + " gates)."
                        : "Gates loaded: " + gates.length,
                    false
                );
            })
            .catch(function (err) {
                showBanner(
                    "Failed to load gates: " + (err && err.message ? err.message : "Unknown error"),
                    true
                );
            })
            .finally(function () {
                if (btn) btn.disabled = false;
                loadClosureCockpit();
            });
    }

    function loadClosureCockpit() {
        if (!window.ManageAuth) return;
        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai-stack/closure-cockpit")
            .then(function (resp) {
                var data = apiData(resp);
                if (!data || (!data.gate_stack && !data.closure_items)) return;
                renderClosureCockpit(data);
            })
            .catch(function () {
                /* optional section */
            });
    }

    function renderClosureCockpit(data) {
        var sectionEl = $("readiness-closure-section");
        var contentEl = $("readiness-closure-content");
        if (!sectionEl || !contentEl) return;

        var html = "";
        var items = data.closure_items;
        if (items && Array.isArray(items)) {
            for (var i = 0; i < items.length; i++) {
                var item = items[i];
                var statusClass = "readiness-closure-item";
                if (item.status === "closed") statusClass += " closed";
                else if (item.status === "partial") statusClass += " partial";
                else if (item.status === "open") statusClass += " open";

                html += "<div class=\"" + statusClass + "\">";
                html += "<p class=\"readiness-closure-title\">";
                html += escapeHtml(item.name || item.id || "Closure Item");
                html += " <span class=\"readiness-closure-status\">(" + escapeHtml(item.status) + ")</span>";
                html += "</p>";
                if (item.message) {
                    html += "<p class=\"readiness-closure-message\">" + escapeHtml(item.message) + "</p>";
                }
                html += "</div>";
            }
        } else if (data.gate_stack && Array.isArray(data.gate_stack)) {
            for (var j = 0; j < data.gate_stack.length; j++) {
                var row = data.gate_stack[j];
                html += "<div class=\"readiness-closure-item\">";
                html += "<p class=\"readiness-closure-title\"><strong>" + escapeHtml(row.gate_id || row.id || "Gate") + "</strong>";
                if (row.status) html += " <span class=\"readiness-closure-status\">(" + escapeHtml(row.status) + ")</span>";
                html += "</p>";
                if (row.reason || row.message) {
                    html += "<p class=\"readiness-closure-message\">" + escapeHtml(row.reason || row.message) + "</p>";
                }
                html += "</div>";
            }
        }

        var hasContent = Boolean(html);
        if (hasContent) contentEl.innerHTML = html;
        if (window.ManageReadinessDeck && window.ManageReadinessDeck.setClosureVisible) {
            window.ManageReadinessDeck.setClosureVisible(hasContent);
        } else if (sectionEl) {
            sectionEl.hidden = !hasContent;
        }
    }

    function renderSummary(summary) {
        summary = summary || {
            total_gates: 0,
            closed_gates: 0,
            partial_gates: 0,
            open_gates: 0,
            closure_percent: 0
        };

        if (window.ManageReadinessDeck && window.ManageReadinessDeck.syncSummary) {
            window.ManageReadinessDeck.syncSummary(summary);
        }

        var progressEl = $("readiness-progress-fill");
        var lastCheckedEl = $("readiness-last-checked");
        if (progressEl) progressEl.style.width = summary.closure_percent + "%";
        if (lastCheckedEl) {
            lastCheckedEl.textContent = "Last checked: " + new Date().toLocaleString();
        }
    }

    function applyFilters() {
        var statusFilter = ($("readiness-filter-status") || {}).value || "";
        var serviceFilter = ($("readiness-filter-service") || {}).value || "";
        var searchTerm = (($("readiness-search") || {}).value || "").toLowerCase();

        filteredGates = gates.filter(function (gate) {
            var statusMatch = !statusFilter || gate.status === statusFilter;
            var serviceMatch = !serviceFilter || gate.owner_service === serviceFilter;
            var searchMatch =
                !searchTerm ||
                String(gate.gate_id || "").toLowerCase().indexOf(searchTerm) >= 0 ||
                String(gate.gate_name || "").toLowerCase().indexOf(searchTerm) >= 0;
            return statusMatch && serviceMatch && searchMatch;
        });

        renderGatesList();
    }

    function renderGatesList() {
        var listEl = $("readiness-gates-list");
        var countEl = $("readiness-gate-count-display");
        if (!listEl) return;

        var html = "";
        if (filteredGates.length === 0) {
            html = "<p class=\"manage-dx-empty\">No gates match the current filters.</p>";
        } else {
            for (var i = 0; i < filteredGates.length; i++) {
                html += renderGateItem(filteredGates[i]);
            }
        }

        listEl.innerHTML = html;
        if (countEl) {
            countEl.textContent = "Showing " + filteredGates.length + " of " + gates.length + " gates";
        }

        var items = listEl.querySelectorAll(".readiness-gate-item");
        for (var j = 0; j < items.length; j++) {
            (function (item) {
                item.addEventListener("click", function () {
                    var gateId = item.dataset.gateId;
                    var gate = gates.find(function (g) {
                        return g.gate_id === gateId;
                    });
                    if (gate) showGateDetail(gate);
                });
            })(items[j]);
        }
    }

    function renderGateItem(gate) {
        return (
            "<div class=\"readiness-gate-item mui-card\" data-gate-id=\"" +
            escapeHtml(gate.gate_id) +
            "\">" +
            "<span class=\"" +
            statusBadgeClass(gate.status) +
            "\">" +
            escapeHtml(gate.status) +
            "</span>" +
            "<div class=\"readiness-gate-info\">" +
            "<p class=\"readiness-gate-name\">" +
            escapeHtml(gate.gate_name) +
            "</p>" +
            "<p class=\"readiness-gate-meta\">" +
            escapeHtml(gate.gate_id) +
            "<span class=\"readiness-gate-owner\">" +
            escapeHtml(gate.owner_service) +
            "</span>" +
            "</p>" +
            "</div>" +
            "<p class=\"readiness-gate-hint muted\">Click for details</p>" +
            "</div>"
        );
    }

    function showGateDetail(gate) {
        var modal = $("readiness-detail-modal");
        if (!modal) return;

        $("readiness-detail-name").textContent = gate.gate_name || "";
        var statusBadgeEl = $("readiness-detail-status-badge");
        if (statusBadgeEl) {
            statusBadgeEl.className = statusBadgeClass(gate.status);
            statusBadgeEl.textContent = gate.status;
        }
        $("readiness-detail-gate-id").textContent = gate.gate_id;
        $("readiness-detail-owner").textContent = gate.owner_service;
        $("readiness-detail-status").textContent = gate.status;
        $("readiness-detail-truth-source").textContent = gate.truth_source || "unknown";
        $("readiness-detail-last-checked").textContent = gate.last_checked_at
            ? new Date(gate.last_checked_at).toLocaleString()
            : "Never";
        $("readiness-detail-checked-by").textContent = gate.checked_by || "system";
        $("readiness-detail-expected").textContent = gate.expected_evidence || "(Not specified)";
        $("readiness-detail-actual").textContent = gate.actual_evidence || "(No evidence collected)";
        var evidencePathEl = $("readiness-detail-evidence-path");
        if (evidencePathEl) {
            evidencePathEl.innerHTML = gate.evidence_path
                ? "<code>" + escapeHtml(gate.evidence_path) + "</code>"
                : "(Not available)";
        }

        var reasonSectionEl = $("readiness-detail-reason-section");
        var reasonEl = $("readiness-detail-reason");
        if (reasonSectionEl && reasonEl) {
            var hasReason = gate.reason && String(gate.reason).trim();
            if (hasReason) reasonEl.textContent = gate.reason;
            reasonSectionEl.hidden = !hasReason;
        }

        var remediationSectionEl = $("readiness-detail-remediation-section");
        var remediationEl = $("readiness-detail-remediation");
        var stepsEl = $("readiness-detail-steps");
        if (remediationSectionEl && remediationEl && stepsEl) {
            var hasRemediation = gate.remediation && String(gate.remediation).trim();
            if (hasRemediation) {
                remediationEl.textContent = gate.remediation;
                var stepsHtml = "";
                if (gate.remediation_steps && gate.remediation_steps.length > 0) {
                    stepsHtml = "<ol class=\"readiness-detail-steps\">";
                    for (var i = 0; i < gate.remediation_steps.length; i++) {
                        stepsHtml += "<li>" + escapeHtml(gate.remediation_steps[i]) + "</li>";
                    }
                    stepsHtml += "</ol>";
                }
                stepsEl.innerHTML = stepsHtml;
            } else {
                stepsEl.innerHTML = "";
            }
            remediationSectionEl.hidden = !hasRemediation;
        }

        var diagnosisSectionEl = $("readiness-detail-diagnosis-section");
        var diagnosisCheckEl = $("readiness-detail-diagnosis-check");
        var diagnosisLinkEl = $("readiness-detail-diagnosis-link");
        if (diagnosisSectionEl && diagnosisCheckEl && diagnosisLinkEl) {
            var hasDiagnosis = Boolean(gate.diagnosis_check_id);
            if (hasDiagnosis) {
                diagnosisCheckEl.textContent = gate.diagnosis_check_id;
                diagnosisLinkEl.href = gate.diagnosis_link || "/manage/diagnosis";
            }
            diagnosisSectionEl.hidden = !hasDiagnosis;
        }

        modal.hidden = false;
    }

    function hideGateDetail() {
        var modal = $("readiness-detail-modal");
        if (modal) modal.hidden = true;
    }

    function setupEventListeners() {
        var refreshBtn = $("readiness-refresh-btn");
        var statusFilter = $("readiness-filter-status");
        var serviceFilter = $("readiness-filter-service");
        var searchInput = $("readiness-search");
        var closeModalBtn = $("readiness-detail-close");
        var closeDetailBtn = $("readiness-detail-close-btn");
        var backdrop = document.querySelector(".readiness-detail-backdrop");
        var modal = $("readiness-detail-modal");

        if (refreshBtn) {
            refreshBtn.addEventListener("click", function () {
                loadGates(true);
            });
        }
        if (statusFilter) statusFilter.addEventListener("change", applyFilters);
        if (serviceFilter) serviceFilter.addEventListener("change", applyFilters);
        if (searchInput) searchInput.addEventListener("input", applyFilters);
        if (closeModalBtn) closeModalBtn.addEventListener("click", hideGateDetail);
        if (closeDetailBtn) closeDetailBtn.addEventListener("click", hideGateDetail);
        if (backdrop) backdrop.addEventListener("click", hideGateDetail);
        if (modal) {
            modal.addEventListener("click", function (e) {
                if (e.target === modal) hideGateDetail();
            });
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        applyUrlFilters();
        setupEventListeners();
        if (window.ManageUI && typeof window.ManageUI.scan === "function") {
            window.ManageUI.scan(document.querySelector(".manage-readiness-page") || document);
        }
        if (!window.ManageAuth) {
            showBanner("ManageAuth is not loaded — cannot fetch gates.", true);
            return;
        }
        window.ManageAuth.ensureAuth()
            .then(function () {
                return loadGates(true);
            })
            .catch(function (err) {
                showBanner(err && err.message ? err.message : "Authentication required.", true);
            });
    });
})();
