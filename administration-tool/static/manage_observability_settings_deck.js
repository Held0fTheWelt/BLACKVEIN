/**
 * manage_observability_settings_deck.js
 *
 * Operator-deck overlay for Observability Settings. Layered on top of
 * manage_observability_settings.js without modifying it.
 *
 * Responsibilities:
 *   - Mirror header-pill text into the status cards (so the Status section
 *     shows the same info as the pills).
 *   - Classify pill colors (ok / warn / fail) based on current text.
 *   - Wire inline result chips for every action button.
 *   - Mirror banner text to the header chip + active section's chip.
 */
(function () {
  "use strict";
  if (!window.ManageUI) return;

  function $(id) { return document.getElementById(id); }

  // -------------------------------------------------------------------------
  // Pill + card sync.
  // -------------------------------------------------------------------------
  var PILLS = [
    { src: "manage-obs-status-enabled",    card: "manage-obs-status-enabled-card",    pill: "manage-obs-pill-status",     positive: ["enabled"] },
    { src: "manage-obs-status-credential", card: "manage-obs-status-credential-card", pill: "manage-obs-pill-credential", positive: ["configured"], negative: ["not configured"] },
    { src: "manage-obs-status-health",     card: "manage-obs-status-health-card",     pill: "manage-obs-pill-health",     positive: ["healthy", "connected"], negative: ["unhealthy", "failed", "missing", "invalid", "mismatch", "delayed", "forbidden", "disabled", "unconfigured"] },
    { src: "manage-obs-status-tested",     card: "manage-obs-status-tested-card",     pill: "manage-obs-pill-tested",     positive: [], negative: ["never"] }
  ];

  function classifyPill(pillEl, text, def) {
    if (!pillEl) return;
    pillEl.classList.remove("mui-pill--ok", "mui-pill--warn", "mui-pill--fail");
    var lower = (text || "").toLowerCase();
    if (def.positive && def.positive.some(function (k) { return lower.indexOf(k) > -1; })) {
      pillEl.classList.add("mui-pill--ok");
      return;
    }
    if (def.negative && def.negative.some(function (k) { return lower.indexOf(k) > -1; })) {
      pillEl.classList.add("mui-pill--warn");
      return;
    }
  }

  function syncOnce() {
    PILLS.forEach(function (def) {
      var src = $(def.src);
      var card = $(def.card);
      var pill = $(def.pill);
      if (!src) return;
      var text = (src.textContent || "").trim() || "—";
      if (card) card.textContent = text;
      classifyPill(pill, text, def);
    });
  }

  function bindPillSync() {
    PILLS.forEach(function (def) {
      var src = $(def.src);
      if (!src) return;
      var obs = new MutationObserver(syncOnce);
      obs.observe(src, { childList: true, characterData: true, subtree: true });
    });
    syncOnce();
  }

  // -------------------------------------------------------------------------
  // Inline action chips + banner mirror (same pattern as runtime_settings).
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

  function truncateHeaderMirror(text, maxLen) {
    maxLen = maxLen || 88;
    if (!text || text.length <= maxLen) return text;
    return text.slice(0, maxLen - 1) + "…";
  }

  function bindBannerMirror(bannerId, successId) {
    function watch(elId, kind) {
      var el = $(elId);
      if (!el) return;
      var last = "";
      var obs = new MutationObserver(function () {
        var text = (el.textContent || "").trim();
        if (text && text !== last) {
          last = text;
          var header = $("manage-obs-header-result");
          if (header) {
            header.__muiToken = (header.__muiToken || 0) + 1;
            ManageUI.setInlineResult(header, kind, truncateHeaderMirror(text));
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
    watch(bannerId, "error");
    watch(successId, "success");
  }

  // -------------------------------------------------------------------------
  // Init
  // -------------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", function () {
    bindPillSync();
    bindBannerMirror("manage-obs-banner", "manage-obs-success");

    bindFeedback("manage-obs-refresh", ["manage-obs-header-result"], "Reloading…", "Reloaded", 1500);
    bindFeedback("manage-obs-save-config", ["manage-obs-config-result"], "Saving configuration…", "Saved", 2200);
    bindFeedback("manage-obs-save-credential", ["manage-obs-credential-result"], "Updating credentials…", "Updated", 2200);
    bindFeedback("manage-obs-test-connection", ["manage-obs-credential-result"], "Testing connection…", "Test finished", 4000);
    bindFeedback("manage-obs-disable", ["manage-obs-danger-result"], "Disabling…", "Disabled", 2200);
  });
})();
