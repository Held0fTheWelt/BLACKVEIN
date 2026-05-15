/**
 * Operator-deck overlay for MCP Operations.
 *
 *   - Lifts overview counters into header pills.
 *   - Inline action chip on Refresh + banner mirror.
 */
(function () {
  "use strict";
  if (!window.ManageUI) return;
  function $(id) { return document.getElementById(id); }

  function makePill(label, value, modifier) {
    var el = document.createElement("span");
    el.className = "mui-pill" + (modifier ? " mui-pill--" + modifier : "");
    var l = document.createElement("span"); l.className = "mui-pill-label"; l.textContent = label;
    var v = document.createElement("span"); v.className = "mui-pill-value"; v.textContent = value;
    el.appendChild(l); el.appendChild(v);
    return el;
  }

  function renderPills() {
    var overview = $("mcp-ops-overview");
    var pills = $("mcp-pills");
    if (!overview || !pills) return;
    var text = overview.textContent || "";
    // Patterns rendered by existing JS:
    //   "Retention (telemetry): N days"
    //   "Open diagnostic cases: N"
    //   "Last 24h: telemetry rows N, errors N"
    var retention = (text.match(/Retention[^:]*:\s*(\d+)/i) || [])[1];
    var openCases = (text.match(/Open diagnostic cases:\s*(\d+)/i) || [])[1];
    var rows24 = (text.match(/telemetry rows\s*(\d+)/i) || [])[1];
    var errors24 = (text.match(/errors\s*(\d+)/i) || [])[1];

    pills.innerHTML = "";
    if (retention != null) pills.appendChild(makePill("Retention", retention + "d", null));
    if (openCases != null) pills.appendChild(makePill("Open cases", openCases, parseInt(openCases, 10) > 0 ? "warn" : "ok"));
    if (rows24 != null) pills.appendChild(makePill("24h rows", rows24, null));
    if (errors24 != null) pills.appendChild(makePill("24h errors", errors24, parseInt(errors24, 10) > 0 ? "fail" : "ok"));
  }

  function bindOverviewSync() {
    var overview = $("mcp-ops-overview");
    if (!overview) return;
    var obs = new MutationObserver(renderPills);
    obs.observe(overview, { childList: true, characterData: true, subtree: true });
    renderPills();
  }

  function bindRefreshFeedback() {
    var btn = $("mcp-ops-refresh");
    var chip = $("mcp-header-result");
    if (!btn || !chip) return;
    btn.addEventListener("click", function () {
      chip.__muiToken = (chip.__muiToken || 0) + 1;
      var token = chip.__muiToken;
      ManageUI.setInlineResult(chip, "info", "Refreshing…");
      setTimeout(function () {
        if (chip.__muiToken !== token) return;
        if (!chip.classList.contains("mui-inline-result--info")) return;
        ManageUI.setInlineResult(chip, "success", "Refreshed");
      }, 1500);
    });
  }

  function bindBannerMirror() {
    function watch(elId, kind) {
      var el = $(elId); if (!el) return;
      var last = "";
      var obs = new MutationObserver(function () {
        var text = (el.textContent || "").trim();
        if (text && text !== last) {
          last = text;
          var chip = $("mcp-header-result");
          if (chip) {
            chip.__muiToken = (chip.__muiToken || 0) + 1;
            ManageUI.setInlineResult(chip, kind, text);
          }
        }
      });
      obs.observe(el, { childList: true, characterData: true, subtree: true });
    }
    watch("mcp-ops-banner", "error");
    watch("mcp-ops-success", "success");
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindOverviewSync();
    bindRefreshFeedback();
    bindBannerMirror();
  });
})();
