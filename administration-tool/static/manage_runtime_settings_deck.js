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
  function bindInlineResult(btnId, resultId, runningText) {
    var btn = $(btnId);
    var out = $(resultId);
    if (!btn || !out) return;
    btn.addEventListener("click", function () {
      ManageUI.setInlineResult(out, "info", runningText || "Running…");
    });
  }

  function bindBannerMirror(bannerId, successId, resultIds) {
    function watch(elId, kind) {
      var el = $(elId);
      if (!el) return;
      var last = "";
      var obs = new MutationObserver(function () {
        var text = (el.textContent || "").trim();
        if (text && text !== last) {
          last = text;
          // Mirror into whichever result chip belongs to the active section.
          var deck = document.querySelector("[data-mui-deck]");
          var active = deck && deck.querySelector(".mui-deck-section.is-active");
          if (active) {
            var chip = active.querySelector(".mui-inline-result");
            if (chip) ManageUI.setInlineResult(chip, kind, text);
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
    bindInlineResult("manage-rs-save-settings", "manage-rs-advanced-result", "Saving advanced settings…");
    bindInlineResult("manage-sre-save", "manage-sre-result", "Saving Story Runtime Experience…");
    bindBannerMirror("manage-rs-banner", "manage-rs-success");
    bindBannerMirror("manage-sre-banner", "manage-sre-success");
  });
})();
