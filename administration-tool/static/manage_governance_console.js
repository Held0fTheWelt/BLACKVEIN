(function () {
  "use strict";

  function escapeHtml(value) {
    if (value == null) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function showStatus(message, isError) {
    var errorEl = document.getElementById("gov-console-error");
    var statusEl = document.getElementById("gov-console-status");
    if (errorEl) {
      errorEl.hidden = true;
      errorEl.textContent = "";
    }
    if (statusEl) {
      statusEl.hidden = true;
      statusEl.textContent = "";
    }
    if (isError && errorEl) {
      errorEl.hidden = false;
      errorEl.textContent = message;
      return;
    }
    if (!isError && statusEl) {
      statusEl.hidden = false;
      statusEl.textContent = message;
    }
  }

  function renderJson(targetId, payload, label) {
    var el = document.getElementById(targetId);
    if (!el) return;
    if (window.ManageUI && typeof window.ManageUI.jsonViewer === "function") {
      window.ManageUI.jsonViewer(el, payload, {
        label: label || el.dataset.jsonLabel || targetId,
      });
      return;
    }
    el.textContent = JSON.stringify(payload, null, 2);
  }

  function buildUrl(path, params) {
    var search = new URLSearchParams();
    Object.keys(params).forEach(function (key) {
      var value = params[key];
      if (value != null && String(value).trim() !== "") {
        search.set(key, String(value).trim());
      }
    });
    var query = search.toString();
    return query ? path + "?" + query : path;
  }

  async function api(path) {
    if (!window.ManageAuth || typeof window.ManageAuth.apiFetchWithAuth !== "function") {
      throw new Error("ManageAuth bridge unavailable");
    }
    var res = await window.ManageAuth.apiFetchWithAuth(path);
    if (res && typeof res === "object" && Object.prototype.hasOwnProperty.call(res, "ok")) {
      return res.data || {};
    }
    return res || {};
  }

  async function loadGovernanceConsole() {
    var sessionId = (document.getElementById("gov-console-session-id") || {}).value || "";
    var aspect = (document.getElementById("gov-console-aspect-filter") || {}).value || "";
    var moduleId = (document.getElementById("gov-console-module-id") || {}).value || "";

    var common = { session_id: sessionId };
    var jobs = [
      ["gov-runtime-readiness", buildUrl("/api/v1/admin/governance/runtime-readiness-authority", common), "Runtime Readiness"],
      ["gov-adr0041-authority", buildUrl("/api/v1/admin/governance/adr0041-authority-state", common), "Capability Authority"],
      ["gov-capability-matrix", buildUrl("/api/v1/admin/governance/capability-matrix", common), "Capability Matrix"],
      ["gov-validator-registry", "/api/v1/admin/governance/validators/registry", "Validator Registry"],
      ["gov-evidence", "/api/v1/admin/governance/evidence/langfuse-mcp", "Langfuse / MCP"],
      ["gov-ledger", buildUrl("/api/v1/admin/governance/runtime-aspect-ledger", { session_id: sessionId, aspect: aspect }), "Runtime Aspect Ledger"],
      ["gov-narrative-systems", buildUrl("/api/v1/admin/governance/narrative-systems", { session_id: sessionId, module_id: moduleId }), "Runtime Systems"],
      ["gov-feature-flags", "/api/v1/admin/governance/feature-flags", "Feature Flag Ownership"],
    ];

    showStatus("Loading governance projections...", false);
    await Promise.all(
      jobs.map(async function (job) {
        var target = job[0];
        var path = job[1];
        try {
          var data = await api(path);
          renderJson(target, data, job[2]);
        } catch (err) {
          renderJson(
            target,
            { warning: "endpoint_unavailable", detail: String(err && err.message ? err.message : err) },
            job[2]
          );
        }
      })
    );
    var section = document.querySelector('[data-page="governance-console"]');
    if (window.ManageUI && typeof window.ManageUI.scan === "function") {
      window.ManageUI.scan(section || document);
    }
    showStatus("Governance projections refreshed.", false);
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.ManageAuth || typeof window.ManageAuth.ensureAuth !== "function") {
      showStatus("ManageAuth unavailable", true);
      return;
    }
    var refreshBtn = document.getElementById("gov-console-refresh");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        loadGovernanceConsole().catch(function (err) {
          showStatus("Governance refresh failed: " + (err && err.message ? err.message : "unknown error"), true);
        });
      });
    }
    window.ManageAuth.ensureAuth()
      .then(loadGovernanceConsole)
      .catch(function (err) {
        showStatus("Auth check failed: " + (err && err.message ? err.message : "unauthorized"), true);
      });
  });
})();
