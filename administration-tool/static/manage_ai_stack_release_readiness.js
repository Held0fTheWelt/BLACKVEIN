/**
 * AI Stack Release Readiness — Gate management dashboard.
 *
 * Displays canonical readiness gates with filtering, search, and detail view.
 * Each gate shows: status, owner service, evidence, and remediation guidance.
 */
(function() {
    var gates = [];
    var filteredGates = [];

    function escapeHtml(s) {
        if (s == null) return "";
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function statusBadgeClass(status) {
        var base = "readiness-status-badge";
        if (status === "closed") return base + " readiness-status-badge--closed";
        if (status === "partial") return base + " readiness-status-badge--partial";
        if (status === "open") return base + " readiness-status-badge--open";
        return base;
    }

    function showBanner(msg, isError) {
        var el = document.getElementById(isError ? "readiness-banner" : "readiness-success");
        if (!el) return;
        el.textContent = msg;
        el.style.display = "block";
        if (!isError) {
            setTimeout(function() {
                el.style.display = "none";
            }, 4000);
        }
    }

    function loadGates() {
        var btn = document.getElementById("readiness-refresh-btn");
        if (btn) btn.disabled = true;

        // Load gates
        fetch("/api/v1/admin/ai-stack/release-readiness/gates", {
            method: "GET",
            headers: { "Accept": "application/json" }
        })
            .then(function(r) {
                if (!r.ok) throw new Error("HTTP " + r.status);
                return r.json();
            })
            .then(function(resp) {
                if (resp.success && resp.data && resp.data.gates) {
                    gates = resp.data.gates;
                    showBanner("Gates loaded: " + gates.length, false);
                    applyFilters();
                    renderSummary(resp.data.summary);
                } else {
                    showBanner("No gates returned", true);
                }
            })
            .catch(function(err) {
                showBanner("Failed to load gates: " + err.message, true);
            })
            .finally(function() {
                if (btn) btn.disabled = false;
            });

        // Load closure cockpit (optional, doesn't fail if unavailable)
        loadClosureCockpit();
    }

    function loadClosureCockpit() {
        fetch("/api/v1/admin/ai-stack/closure-cockpit", {
            method: "GET",
            headers: { "Accept": "application/json" }
        })
            .then(function(r) {
                if (!r.ok) return null;
                return r.json();
            })
            .then(function(resp) {
                if (resp && resp.data) {
                    renderClosureCockpit(resp.data);
                }
            })
            .catch(function(err) {
                // Silent fail - closure cockpit is optional
            });
    }

    function renderClosureCockpit(data) {
        var sectionEl = document.getElementById("readiness-closure-section");
        var contentEl = document.getElementById("readiness-closure-content");

        if (!sectionEl || !contentEl) return;

        var html = "";

        // Render closure items
        if (data.closure_items && Array.isArray(data.closure_items)) {
            for (var i = 0; i < data.closure_items.length; i++) {
                var item = data.closure_items[i];
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
        }

        if (html) {
            contentEl.innerHTML = html;
            sectionEl.style.display = "block";
        } else {
            sectionEl.style.display = "none";
        }
    }

    function renderSummary(summary) {
        if (!summary) {
            summary = {
                total_gates: 0,
                closed_gates: 0,
                partial_gates: 0,
                open_gates: 0,
                closure_percent: 0
            };
        }

        var closureEl = document.getElementById("readiness-closure-percent");
        var closedEl = document.getElementById("readiness-closed-count");
        var partialEl = document.getElementById("readiness-partial-count");
        var openEl = document.getElementById("readiness-open-count");
        var totalEl = document.getElementById("readiness-total-count");
        var progressEl = document.getElementById("readiness-progress-fill");
        var lastCheckedEl = document.getElementById("readiness-last-checked");

        if (closureEl) closureEl.textContent = summary.closure_percent + "%";
        if (closedEl) closedEl.textContent = summary.closed_gates;
        if (partialEl) partialEl.textContent = summary.partial_gates;
        if (openEl) openEl.textContent = summary.open_gates;
        if (totalEl) totalEl.textContent = summary.total_gates;
        if (progressEl) progressEl.style.width = summary.closure_percent + "%";

        var now = new Date();
        if (lastCheckedEl) {
            lastCheckedEl.textContent = "Last checked: " + now.toLocaleString();
        }
    }

    function applyFilters() {
        var statusFilter = (document.getElementById("readiness-filter-status") || {}).value || "";
        var serviceFilter = (document.getElementById("readiness-filter-service") || {}).value || "";
        var searchTerm = ((document.getElementById("readiness-search") || {}).value || "").toLowerCase();

        filteredGates = gates.filter(function(gate) {
            var statusMatch = !statusFilter || gate.status === statusFilter;
            var serviceMatch = !serviceFilter || gate.owner_service === serviceFilter;
            var searchMatch = !searchTerm ||
                gate.gate_id.toLowerCase().indexOf(searchTerm) >= 0 ||
                gate.gate_name.toLowerCase().indexOf(searchTerm) >= 0;
            return statusMatch && serviceMatch && searchMatch;
        });

        renderGatesList();
    }

    function renderGatesList() {
        var listEl = document.getElementById("readiness-gates-list");
        var countEl = document.getElementById("readiness-gate-count-display");

        if (!listEl) return;

        var html = "";
        if (filteredGates.length === 0) {
            html = "<p class=\"muted\">No gates match the current filters.</p>";
        } else {
            for (var i = 0; i < filteredGates.length; i++) {
                var gate = filteredGates[i];
                html += renderGateItem(gate);
            }
        }

        listEl.innerHTML = html;

        if (countEl) {
            countEl.textContent = "Showing " + filteredGates.length + " of " + gates.length + " gates";
        }

        // Attach click handlers
        var items = listEl.querySelectorAll(".readiness-gate-item");
        for (var j = 0; j < items.length; j++) {
            (function(item) {
                item.addEventListener("click", function() {
                    var gateId = item.dataset.gateId;
                    var gate = gates.find(function(g) { return g.gate_id === gateId; });
                    if (gate) showGateDetail(gate);
                });
            })(items[j]);
        }
    }

    function renderGateItem(gate) {
        return (
            "<div class=\"readiness-gate-item\" data-gate-id=\"" + escapeHtml(gate.gate_id) + "\">" +
            "<span class=\"" + statusBadgeClass(gate.status) + "\">" + escapeHtml(gate.status) + "</span>" +
            "<div class=\"readiness-gate-info\">" +
            "<p class=\"readiness-gate-name\">" + escapeHtml(gate.gate_name) + "</p>" +
            "<p class=\"readiness-gate-meta\">" +
            escapeHtml(gate.gate_id) +
            "<span class=\"readiness-gate-owner\">" + escapeHtml(gate.owner_service) + "</span>" +
            "</p>" +
            "</div>" +
            "<div style=\"text-align: right; font-size: 0.875rem; color: var(--text-muted, #666);\">" +
            "Click to view details →" +
            "</div>" +
            "</div>"
        );
    }

    function showGateDetail(gate) {
        var modal = document.getElementById("readiness-detail-modal");
        if (!modal) return;

        // Populate detail fields
        var nameEl = document.getElementById("readiness-detail-name");
        var statusBadgeEl = document.getElementById("readiness-detail-status-badge");
        var gateIdEl = document.getElementById("readiness-detail-gate-id");
        var ownerEl = document.getElementById("readiness-detail-owner");
        var statusEl = document.getElementById("readiness-detail-status");
        var truthSourceEl = document.getElementById("readiness-detail-truth-source");
        var lastCheckedEl = document.getElementById("readiness-detail-last-checked");
        var checkedByEl = document.getElementById("readiness-detail-checked-by");
        var expectedEl = document.getElementById("readiness-detail-expected");
        var actualEl = document.getElementById("readiness-detail-actual");
        var evidencePathEl = document.getElementById("readiness-detail-evidence-path");
        var reasonEl = document.getElementById("readiness-detail-reason");
        var reasonSectionEl = document.getElementById("readiness-detail-reason-section");
        var remediationEl = document.getElementById("readiness-detail-remediation");
        var remediationSectionEl = document.getElementById("readiness-detail-remediation-section");
        var stepsEl = document.getElementById("readiness-detail-steps");
        var diagnosisSectionEl = document.getElementById("readiness-detail-diagnosis-section");
        var diagnosisCheckEl = document.getElementById("readiness-detail-diagnosis-check");
        var diagnosisLinkEl = document.getElementById("readiness-detail-diagnosis-link");

        if (nameEl) nameEl.textContent = gate.gate_name || "";
        if (statusBadgeEl) {
            statusBadgeEl.className = statusBadgeClass(gate.status);
            statusBadgeEl.textContent = gate.status;
        }
        if (gateIdEl) gateIdEl.textContent = gate.gate_id;
        if (ownerEl) ownerEl.textContent = gate.owner_service;
        if (statusEl) statusEl.textContent = gate.status;
        if (truthSourceEl) truthSourceEl.textContent = gate.truth_source || "unknown";
        if (lastCheckedEl) lastCheckedEl.textContent = gate.last_checked_at ? new Date(gate.last_checked_at).toLocaleString() : "Never";
        if (checkedByEl) checkedByEl.textContent = gate.checked_by || "system";

        if (expectedEl) expectedEl.textContent = gate.expected_evidence || "(Not specified)";
        if (actualEl) actualEl.textContent = gate.actual_evidence || "(No evidence collected)";
        if (evidencePathEl) {
            if (gate.evidence_path) {
                evidencePathEl.innerHTML = "<code>" + escapeHtml(gate.evidence_path) + "</code>";
            } else {
                evidencePathEl.textContent = "(Not available)";
            }
        }

        // Show reason if present and non-empty
        if (reasonSectionEl && reasonEl) {
            if (gate.reason && gate.reason.trim()) {
                reasonEl.textContent = gate.reason;
                reasonSectionEl.style.display = "block";
            } else {
                reasonSectionEl.style.display = "none";
            }
        }

        // Show remediation if present and non-empty
        if (remediationSectionEl && remediationEl && stepsEl) {
            if (gate.remediation && gate.remediation.trim()) {
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
                remediationSectionEl.style.display = "block";
            } else {
                remediationSectionEl.style.display = "none";
            }
        }

        // Show diagnosis link if available
        if (diagnosisSectionEl && diagnosisCheckEl && diagnosisLinkEl) {
            if (gate.diagnosis_check_id) {
                diagnosisCheckEl.textContent = gate.diagnosis_check_id;
                if (gate.diagnosis_link) {
                    diagnosisLinkEl.href = gate.diagnosis_link;
                }
                diagnosisSectionEl.style.display = "block";
            } else {
                diagnosisSectionEl.style.display = "none";
            }
        }

        modal.style.display = "flex";
    }

    function hideGateDetail() {
        var modal = document.getElementById("readiness-detail-modal");
        if (modal) modal.style.display = "none";
    }

    function setupEventListeners() {
        var refreshBtn = document.getElementById("readiness-refresh-btn");
        var statusFilter = document.getElementById("readiness-filter-status");
        var serviceFilter = document.getElementById("readiness-filter-service");
        var searchInput = document.getElementById("readiness-search");
        var closeModalBtn = document.getElementById("readiness-detail-close");
        var closeDetailBtn = document.getElementById("readiness-detail-close-btn");
        var backdrop = document.querySelector(".readiness-detail-backdrop");
        var modal = document.getElementById("readiness-detail-modal");

        if (refreshBtn) refreshBtn.addEventListener("click", loadGates);
        if (statusFilter) statusFilter.addEventListener("change", applyFilters);
        if (serviceFilter) serviceFilter.addEventListener("change", applyFilters);
        if (searchInput) searchInput.addEventListener("input", applyFilters);
        if (closeModalBtn) closeModalBtn.addEventListener("click", hideGateDetail);
        if (closeDetailBtn) closeDetailBtn.addEventListener("click", hideGateDetail);
        if (backdrop) backdrop.addEventListener("click", hideGateDetail);
        if (modal) {
            modal.addEventListener("click", function(e) {
                if (e.target === modal) hideGateDetail();
            });
        }
    }

    document.addEventListener("DOMContentLoaded", function() {
        setupEventListeners();
        loadGates();
    });
})();
