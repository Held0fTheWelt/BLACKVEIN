/**
 * Governance Health Panels Controller
 * Loads truthful Phase-C runtime, cost, and evaluation data through the admin proxy.
 */

class GovernanceHealthPanelsController {
    constructor() {
        this.currentSessionId = null;
        this.costChart = null;
        this.apiBase = (window.FrontendConfig && typeof window.FrontendConfig.getApiBaseUrl === "function")
            ? window.FrontendConfig.getApiBaseUrl()
            : "";
        this.init();
    }

    init() {
        this.attachEventListeners();
        this.initializeCharts();
    }

    attachEventListeners() {
        const loadBtn = document.getElementById("load_session_btn");
        const sessionInput = document.getElementById("session_id_input");
        const panelRefreshBtns = document.querySelectorAll(".panel-refresh");
        const applyOverrideBtn = document.getElementById("apply_budget_override_btn");

        if (loadBtn) loadBtn.addEventListener("click", () => this.loadSession());
        if (sessionInput) {
            sessionInput.addEventListener("keypress", (event) => {
                if (event.key === "Enter") this.loadSession();
            });
        }
        panelRefreshBtns.forEach((btn) => btn.addEventListener("click", () => this.refreshAllPanels()));
        if (applyOverrideBtn) {
            applyOverrideBtn.addEventListener("click", () => this.applyBudgetOverride());
        }
    }

    apiFetch(path, opts) {
        if (window.FrontendConfig && typeof window.FrontendConfig.apiFetch === "function") {
            return window.FrontendConfig.apiFetch(path, opts);
        }
        const url = `${this.apiBase.replace(/\/$/, "")}${path}`;
        return fetch(url, opts || {}).then((response) => response.json());
    }

    loadSession() {
        const sessionInput = document.getElementById("session_id_input");
        const sessionId = sessionInput ? sessionInput.value.trim() : "";
        if (!sessionId) {
            this.setStatus("Please enter a session ID", "error");
            return;
        }
        this.currentSessionId = sessionId;
        this.setStatus("Loading live runtime evidence...", "info");
        this.fetchSessionData(sessionId);
    }

    async fetchSessionData(sessionId) {
        const today = new Date().toISOString().slice(0, 10);
        try {
            const [summaryEnvelope, dailyEnvelope, weeklyEnvelope] = await Promise.all([
                this.apiFetch(`/api/v1/admin/mvp4/game/session/${encodeURIComponent(sessionId)}/summary`),
                this.apiFetch(`/api/v1/admin/mvp4/costs/daily?date=${today}`),
                this.apiFetch(`/api/v1/admin/mvp4/costs/weekly?week_start=${today}`),
            ]);

            const summary = summaryEnvelope && summaryEnvelope.data ? summaryEnvelope.data : {};
            const dailyReport = dailyEnvelope && dailyEnvelope.data ? dailyEnvelope.data : {};
            const weeklyReport = weeklyEnvelope && weeklyEnvelope.data ? weeklyEnvelope.data : {};

            this.updatePanels(summary, dailyReport, weeklyReport);
            this.setStatus("Session loaded successfully", "success");
        } catch (error) {
            console.error("Failed to load governance panels:", error);
            this.setStatus(`Error loading session: ${error}`, "error");
        }
    }

    updatePanels(summary, dailyReport, weeklyReport) {
        const diagnostics = summary && summary.diagnostics_envelope ? summary.diagnostics_envelope : {};
        const budgetStatus = summary && summary.budget_status ? summary.budget_status : {};
        const costSummary = summary && summary.cost_summary ? summary.cost_summary : {};
        const evaluation = summary && summary.evaluation ? summary.evaluation : {};

        this.updateHealthStatus(diagnostics, budgetStatus);
        this.updateTokenAndCost(budgetStatus, costSummary);
        this.updateBudgetControls(budgetStatus);
        this.updateDegradationTimeline(diagnostics.degradation_timeline || []);
        this.updateEvaluationPanels(evaluation);
        this.updateCostBreakdown(costSummary.cost_breakdown || {});
        this.updateCostDashboard(costSummary, dailyReport, weeklyReport);
    }

    updateHealthStatus(diagnostics, budgetStatus) {
        this.setText("quality_class", diagnostics.quality_class || "unknown");
        this.setText("degradation_level", budgetStatus.degradation_level || "none");
    }

    updateTokenAndCost(budgetStatus, costSummary) {
        const usedTokens = Number(budgetStatus.used_tokens || 0);
        const totalBudget = Number(budgetStatus.total_budget || 0);
        const usagePercent = Number(budgetStatus.usage_percent || 0);

        this.setText("tokens_used", usedTokens.toString());
        this.setText("cost_used", this.formatUsd(costSummary.cost_usd || 0));
        this.setText("budget_status", `${usedTokens} / ${totalBudget} tokens`);

        const budgetProgress = document.getElementById("budget_progress");
        if (budgetProgress) budgetProgress.style.width = `${Math.max(0, Math.min(100, usagePercent))}%`;
    }

    updateBudgetControls(budgetStatus) {
        const usedTokens = Number(budgetStatus.used_tokens || 0);
        const totalBudget = Number(budgetStatus.total_budget || 0);
        this.setText("total_budget", `${totalBudget} tokens`);
        this.setText("budget_used", `${usedTokens} tokens`);
        this.setText("budget_remaining", `${Math.max(0, totalBudget - usedTokens)} tokens`);
        this.setText("degradation_strategy", budgetStatus.degradation_strategy || "ldss_shorter");
    }

    updateEvaluationPanels(evaluation) {
        const qualitySummary = evaluation && evaluation.quality_summary ? evaluation.quality_summary : {};
        const dimensions = qualitySummary.dimensions || {};
        this.updateDimensionScore("coherence", dimensions.coherence || {});
        this.updateDimensionScore("authenticity", dimensions.authenticity || {});
        this.updateDimensionScore("player_agency", dimensions.player_agency || {});
        this.updateDimensionScore("immersion", dimensions.immersion || {});
    }

    updateDimensionScore(dimension, summary) {
        const average = Number(summary.average_score || 0);
        const scoreBar = document.getElementById(`${dimension}_score_bar`);
        const scoreSpan = document.getElementById(`${dimension}_score`);

        if (scoreBar) scoreBar.style.width = `${Math.max(0, Math.min(100, (average / 5) * 100))}%`;
        if (scoreSpan) scoreSpan.textContent = summary.sample_count ? `${average.toFixed(1)}/5` : "—";
    }

    updateDegradationTimeline(events) {
        const timelineEl = document.getElementById("degradation_timeline");
        if (!timelineEl) return;

        if (!events || events.length === 0) {
            timelineEl.innerHTML = '<p class="empty-state">No degradation events recorded</p>';
            return;
        }

        timelineEl.innerHTML = events.map((event) => `
            <div class="timeline-item">
                <div class="timeline-timestamp">${this.formatTime(event.timestamp)}</div>
                <div class="timeline-event">
                    <strong>${event.severity || "info"}</strong>: ${event.marker || "unknown"}
                    ${event.recovery_successful ? "Recovered" : "Active"}
                </div>
            </div>
        `).join("");
    }

    updateCostBreakdown(costBreakdown) {
        if (!this.costChart) return;
        const labels = Object.keys(costBreakdown);
        const values = labels.map((label) => Number(costBreakdown[label] || 0));
        this.costChart.data.labels = labels.length ? labels : ["No billed phases"];
        this.costChart.data.datasets[0].data = values.length ? values : [0];
        this.costChart.update();
    }

    updateCostDashboard(costSummary, dailyReport, weeklyReport) {
        this.setText("cost_today", this.formatUsd(dailyReport.total_cost || 0));
        this.setText("cost_week", this.formatUsd(weeklyReport.total_cost || 0));
        this.setText("cost_per_turn", this.formatUsd(costSummary.cost_per_turn_avg || 0));
        const projected = Number(weeklyReport.average_session_cost || 0) || Number(costSummary.cost_usd || 0);
        this.setText("cost_projected", this.formatUsd(projected));
    }

    async applyBudgetOverride() {
        if (!this.currentSessionId) {
            this.setStatus("Please load a session first", "error");
            return;
        }

        const tokensToAdd = parseInt((document.getElementById("tokens_to_add") || {}).value, 10);
        const reasonField = document.getElementById("override_reason");
        const reason = reasonField ? reasonField.value.trim() : "";

        if (Number.isNaN(tokensToAdd) || tokensToAdd <= 0) {
            this.setStatus("Please enter a valid number of tokens", "error");
            return;
        }
        if (!reason) {
            this.setStatus("Please provide a reason for the override", "error");
            return;
        }

        try {
            const result = await this.apiFetch(
                `/api/v1/admin/mvp4/game/session/${encodeURIComponent(this.currentSessionId)}/token-budget/override`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ tokens_to_add: tokensToAdd, reason: reason }),
                },
            );
            if (result && result.ok) {
                this.setStatus(`Budget override applied: ${tokensToAdd} tokens added`, "success");
                if (document.getElementById("tokens_to_add")) document.getElementById("tokens_to_add").value = "";
                if (reasonField) reasonField.value = "";
                this.fetchSessionData(this.currentSessionId);
            } else {
                const error = result && result.error ? result.error : "Unknown error";
                this.setStatus(`Error: ${error}`, "error");
            }
        } catch (error) {
            this.setStatus(`Error applying override: ${error}`, "error");
        }
    }

    refreshAllPanels() {
        if (this.currentSessionId) {
            this.fetchSessionData(this.currentSessionId);
        }
    }

    initializeCharts() {
        const ctx = document.getElementById("cost_breakdown_chart");
        if (!ctx || typeof Chart === "undefined") return;
        this.costChart = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["No billed phases"],
                datasets: [{
                    data: [0],
                    backgroundColor: ["#5b7cfa", "#45b36b", "#f0a202", "#d1495b"],
                }],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: "bottom" },
                },
            },
        });
    }

    setStatus(message, type) {
        const statusEl = document.getElementById("session_status");
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.className = `status-indicator status-${type}`;
        }
    }

    setText(id, value) {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    }

    formatUsd(value) {
        return `$${Number(value || 0).toFixed(4)}`;
    }

    formatTime(timestamp) {
        if (!timestamp) return "—";
        const date = new Date(timestamp);
        return Number.isNaN(date.getTime()) ? "—" : date.toLocaleTimeString();
    }
}

document.addEventListener("DOMContentLoaded", () => {
    window.healthPanelsController = new GovernanceHealthPanelsController();
});
