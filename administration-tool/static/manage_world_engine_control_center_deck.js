/**
 * manage_world_engine_control_center_deck.js
 *
 * Operator-deck overlay for WECC.
 *
 *   - Parses the rendered overview-badges text and renders pills in the header.
 *   - Inline action chips + banner mirror.
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
    var carrier = $("wecc-overview-badges");
    var pills = $("wecc-pills");
    if (!carrier || !pills) return;
    var text = (carrier.textContent || "").trim();
    if (!text) { pills.innerHTML = ""; return; }
    // Parse pattern: "Control plane state: X · Blockers: N · Warnings: M"
    var stateMatch = text.match(/state:\s*([\w-]+)/i);
    var blockMatch = text.match(/blockers:\s*(\d+)/i);
    var warnMatch = text.match(/warnings:\s*(\d+)/i);
    var state = stateMatch ? stateMatch[1] : "unknown";
    var blockers = blockMatch ? parseInt(blockMatch[1], 10) : null;
    var warnings = warnMatch ? parseInt(warnMatch[1], 10) : null;

    var stateMod = (state === "healthy" ? "ok" : (state === "blocked" ? "fail" : "warn"));
    pills.innerHTML = "";
    pills.appendChild(makePill("State", state, stateMod));
    if (blockers != null) pills.appendChild(makePill("Blockers", String(blockers), blockers > 0 ? "fail" : "ok"));
    if (warnings != null) pills.appendChild(makePill("Warnings", String(warnings), warnings > 0 ? "warn" : "ok"));
  }

  function bindOverviewSync() {
    var carrier = $("wecc-overview-badges");
    if (!carrier) return;
    var obs = new MutationObserver(renderPills);
    obs.observe(carrier, { childList: true, characterData: true, subtree: true });
    renderPills();
  }

  // -------------------------------------------------------------------------
  // Inline chips + banner mirror.
  // -------------------------------------------------------------------------
  function activeSectionChip() {
    var deck = document.querySelector("[data-mui-deck]");
    var active = deck && deck.querySelector(".mui-deck-section.is-active");
    return active && active.querySelector(".mui-inline-result");
  }

  function bindFeedback(btnId, chipIds, runningText, doneText, timeoutMs) {
    var btn = $(btnId);
    if (!btn) return;
    btn.addEventListener("click", function () {
      var entries = [];
      chipIds.forEach(function (id) {
        var c = $(id);
        if (c) {
          c.__muiToken = (c.__muiToken || 0) + 1;
          ManageUI.setInlineResult(c, "info", runningText);
          entries.push({ chip: c, token: c.__muiToken });
        }
      });
      if (!doneText || !timeoutMs) return;
      setTimeout(function () {
        entries.forEach(function (e) {
          if (e.chip.__muiToken !== e.token) return;
          if (!e.chip.classList.contains("mui-inline-result--info")) return;
          if ((e.chip.textContent || "") !== runningText) return;
          ManageUI.setInlineResult(e.chip, "success", doneText);
        });
      }, timeoutMs);
    });
  }

  function bindBannerMirror() {
    function watch(elId, kind) {
      var el = $(elId);
      if (!el) return;
      var last = "";
      var obs = new MutationObserver(function () {
        var text = (el.textContent || "").trim();
        if (text && text !== last) {
          last = text;
          var header = $("wecc-header-result");
          if (header) {
            header.__muiToken = (header.__muiToken || 0) + 1;
            ManageUI.setInlineResult(header, kind, text);
          }
          var chip = activeSectionChip();
          if (chip) {
            chip.__muiToken = (chip.__muiToken || 0) + 1;
            ManageUI.setInlineResult(chip, kind, text);
          }
        }
      });
      obs.observe(el, { childList: true, characterData: true, subtree: true });
    }
    watch("wecc-banner", "error");
    watch("wecc-success", "success");
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindOverviewSync();
    bindBannerMirror();
    bindFeedback("wecc-refresh", ["wecc-header-result"], "Reloading…", "Reloaded", 1500);
    bindFeedback("wecc-test", ["wecc-header-result"], "Testing…", "Test finished", 4000);
    bindFeedback("wecc-apply", ["wecc-header-result"], "Applying…", "Applied", 4000);
  });
})();
