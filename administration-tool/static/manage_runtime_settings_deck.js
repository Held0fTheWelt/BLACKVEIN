/**
 * manage_runtime_settings_deck.js
 *
 * Operator-deck overlay for Runtime Settings. Layered on top of
 * manage_runtime_settings.js / manage_story_runtime_experience.js without
 * touching them.
 *
 * Responsibilities:
 *   - Mirror the active preset / override count / drift from rendered text
 *     into the sticky header pills (so they're always visible).
 *   - Render inline result chips next to Save buttons.
 *   - Mark advanced/story rail badges based on override count + drift.
 */
(function () {
  "use strict";
  if (!window.ManageUI) return;

  function $(id) { return document.getElementById(id); }

  // -------------------------------------------------------------------------
  // Sticky header pills, derived from the effective summary list.
  // -------------------------------------------------------------------------
  function parseLine(prefix, ul) {
    if (!ul) return null;
    var nodes = ul.querySelectorAll("li");
    for (var i = 0; i < nodes.length; i++) {
      var t = (nodes[i].textContent || "").trim();
      if (t.indexOf(prefix) === 0) {
        return t.slice(prefix.length).trim();
      }
    }
    return null;
  }

  function syncHeaderPills() {
    var effective = $("manage-rs-effective-summary");
    if (!effective) return;
    var presetPill = $("manage-rs-active-preset-pill");
    var overridePill = $("manage-rs-override-count-pill");
    var driftPillWrap = $("manage-rs-drift-pill");
    var driftPill = $("manage-rs-drift-count-pill");

    var preset = parseLine("Active preset:", effective);
    var overrides = parseLine("Override count:", effective);
    var drift = parseLine("Drift keys:", effective);

    if (presetPill && preset) presetPill.textContent = preset;
    if (overridePill && overrides != null) overridePill.textContent = overrides;
    if (driftPillWrap && driftPill && drift != null) {
      var n = parseInt(drift, 10);
      if (n > 0) {
        driftPillWrap.hidden = false;
        driftPillWrap.classList.add("mui-pill--warn");
        driftPill.textContent = drift;
      } else {
        driftPillWrap.hidden = true;
        driftPill.textContent = "0";
      }
    }
  }

  function bindHeaderSync() {
    var target = $("manage-rs-effective-summary");
    if (!target) return;
    var obs = new MutationObserver(syncHeaderPills);
    obs.observe(target, { childList: true, subtree: true, characterData: true });
    syncHeaderPills();
  }

  // -------------------------------------------------------------------------
  // Inline action chips driven by button clicks + banner text watchers.
  // -------------------------------------------------------------------------
  function activeSectionChip() {
    var deck = document.querySelector("[data-mui-deck]");
    var active = deck && deck.querySelector(".mui-deck-section.is-active");
    return active && active.querySelector(".mui-inline-result");
  }

  /**
   * Wire a click handler that:
   *   - shows "running" feedback immediately,
   *   - upgrades to a "done" success state after `timeoutMs` if nothing else
   *     has overwritten the chip in the meantime (handles silently-succeeding
   *     actions whose existing JS never updates a status banner).
   */
  function bindFeedback(btnId, chipIds, runningText, doneText, timeoutMs) {
    var btn = $(btnId);
    if (!btn) return;
    btn.addEventListener("click", function () {
      var chips = [];
      chipIds.forEach(function (id) {
        var c = id === "__active__" ? activeSectionChip() : $(id);
        if (c) {
          ManageUI.setInlineResult(c, "info", runningText);
          c.__muiRunningText = runningText;
          c.__muiToken = (c.__muiToken || 0) + 1;
          var token = c.__muiToken;
          chips.push({ chip: c, token: token });
        }
      });
      if (!doneText || !timeoutMs) return;
      setTimeout(function () {
        chips.forEach(function (entry) {
          var c = entry.chip;
          if (c.__muiToken !== entry.token) return;             // newer click intervened
          if (!c.classList.contains("mui-inline-result--info")) return; // banner already updated
          if ((c.textContent || "") !== runningText) return;    // text changed by something else
          ManageUI.setInlineResult(c, "success", doneText);
        });
      }, timeoutMs);
    });
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
          // Mirror into both the header chip and the active section's chip.
          var header = $("manage-rs-header-result");
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
    watch(bannerId, "error");
    watch(successId, "success");
  }

  // -------------------------------------------------------------------------
  // Init
  // -------------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", function () {
    bindHeaderSync();

    // Header actions (silent success on refresh/reset/apply — give visible feedback).
    bindFeedback("manage-rs-refresh", ["manage-rs-header-result"], "Reloading…", "Reloaded", 1400);
    bindFeedback("manage-rs-reset-overrides", ["manage-rs-header-result"], "Clearing overrides…", "Overrides cleared", 1400);
    bindFeedback("manage-rs-apply-safe-local", ["manage-rs-header-result"], "Applying safe_local…", "Preset applied", 1400);

    // Inspector save buttons (existing JS shows a banner on success, but we still want
    // an immediate "running" chip near the action).
    bindFeedback("manage-rs-save-settings", ["manage-rs-advanced-result"], "Saving advanced settings…", "Saved", 2200);
    bindFeedback("manage-sre-save", ["manage-sre-result"], "Saving Story Runtime Experience…", "Saved", 2200);
    bindFeedback("manage-sre-refresh", ["manage-sre-result"], "Reloading SRE…", "Reloaded", 1400);

    bindBannerMirror("manage-rs-banner", "manage-rs-success");
    bindBannerMirror("manage-sre-banner", "manage-sre-success");
  });
})();
