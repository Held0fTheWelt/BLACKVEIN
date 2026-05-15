/**
 * Operator-deck overlay for System Diagnosis.
 *
 *   - Parses the rendered #manage-diagnosis-overall block and lifts the
 *     status badge + summary counts into the sticky header pills.
 *   - Inline action chip for Refresh.
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
    var overall = $("manage-diagnosis-overall");
    var pills = $("manage-dx-pills");
    if (!overall || !pills) return;
    var badge = overall.querySelector(".manage-dx-badge");
    var counts = overall.querySelector(".manage-dx-summary-counts");
    if (!badge && !counts) {
      pills.innerHTML = "";
      return;
    }

    var state = badge ? (badge.textContent || "").trim() : "";
    var stateMod = state === "ok" || state === "running" ? "ok" : state === "fail" ? "fail" : "warn";

    pills.innerHTML = "";
    if (state) pills.appendChild(makePill("State", state, stateMod));

    if (counts) {
      var t = counts.textContent || "";
      var running = (t.match(/running:\s*(\d+)/i) || [])[1];
      var initialized = (t.match(/initialized:\s*(\d+)/i) || [])[1];
      var fail = (t.match(/fail:\s*(\d+)/i) || [])[1];
      if (running != null) pills.appendChild(makePill("Running", running, parseInt(running, 10) > 0 ? "ok" : null));
      if (initialized != null) pills.appendChild(makePill("Initialized", initialized, parseInt(initialized, 10) > 0 ? "warn" : null));
      if (fail != null) pills.appendChild(makePill("Fail", fail, parseInt(fail, 10) > 0 ? "fail" : "ok"));
    }
  }

  function bindOverallSync() {
    var overall = $("manage-diagnosis-overall");
    if (!overall) return;
    var obs = new MutationObserver(renderPills);
    obs.observe(overall, { childList: true, characterData: true, subtree: true });
    renderPills();
  }

  function bindRefreshFeedback() {
    var btn = $("manage-diagnosis-refresh");
    var chip = $("manage-dx-header-result");
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

    // Mirror error banner
    var err = $("manage-diagnosis-error");
    if (err) {
      var last = "";
      var obs = new MutationObserver(function () {
        var text = (err.textContent || "").trim();
        if (text && text !== last) {
          last = text;
          chip.__muiToken = (chip.__muiToken || 0) + 1;
          ManageUI.setInlineResult(chip, "error", text);
        }
      });
      obs.observe(err, { childList: true, characterData: true, subtree: true });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindOverallSync();
    bindRefreshFeedback();
  });
})();
