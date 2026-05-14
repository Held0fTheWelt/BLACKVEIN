/**
 * manage_operational_governance_deck.js
 *
 * Operator-deck overlay for AI Runtime Governance. Layered on top of
 * manage_operational_governance.js without changing it:
 *
 *   - Mirrors readiness severity into the sticky header pill + rail badge.
 *   - Tags rail option entries with status badges (ok / warn / off) inferred
 *     from the existing label format ("ON · …  · health:ok · eligible").
 *   - Renders Test / Save outcomes as inline result chips next to the button
 *     (in addition to the toast that fires from the legacy banner).
 *   - Hijacks the banner text-content so that ALSO surfacing as inline result
 *     stays tied to the action that triggered it.
 *
 * The page-level JS keeps owning data + endpoint calls.
 */
(function () {
  "use strict";
  if (!window.ManageUI) return;

  function $(id) { return document.getElementById(id); }

  // -------------------------------------------------------------------------
  // Rail badges: classify each <select> option from its label string.
  // -------------------------------------------------------------------------
  function classifyOption(text) {
    var t = (text || "").toLowerCase();
    if (t.indexOf("off") === 0 || t.indexOf("disabled") !== -1) return "off";
    if (
      t.indexOf("blocked") !== -1 ||
      t.indexOf("not eligible") !== -1 ||
      t.indexOf("not runtime") !== -1 ||
      t.indexOf("fail") !== -1
    ) return "warn";
    if (t.indexOf("health:ok") !== -1 || t.indexOf("ai path ok") !== -1 || t.indexOf("eligible") !== -1) return "ok";
    return "warn";
  }

  function tagOptions(selectId) {
    var sel = $(selectId);
    if (!sel) return;
    Array.prototype.forEach.call(sel.options, function (opt) {
      if (!opt.value) return;
      opt.dataset.muiBadge = classifyOption(opt.textContent);
    });
  }

  function watchAndTag(selectId) {
    var sel = $(selectId);
    if (!sel) return;
    tagOptions(selectId);
    var obs = new MutationObserver(function () { tagOptions(selectId); });
    obs.observe(sel, { childList: true, subtree: true });
  }

  // -------------------------------------------------------------------------
  // Readiness header pill: map severity → ok / warn / fail color.
  // -------------------------------------------------------------------------
  function syncReadinessPill() {
    var pill = document.querySelector("[data-readiness-pill]");
    var badge = $("manage-og-readiness-badge");
    var railBadge = $("manage-og-rail-readiness-badge");
    var railSub = $("manage-og-rail-readiness-sub");
    if (!pill || !badge) return;
    var text = (badge.textContent || "").trim().toLowerCase();
    pill.classList.remove("mui-pill--ok", "mui-pill--warn", "mui-pill--fail");
    var cls = "mui-pill--warn";
    var railCls = "mui-rail-badge--warn";
    if (text === "healthy" || text === "ok") { cls = "mui-pill--ok"; railCls = "mui-rail-badge--ok"; }
    else if (text === "blocked" || text === "error") { cls = "mui-pill--fail"; railCls = "mui-rail-badge--fail"; }
    pill.classList.add(cls);
    if (railBadge) {
      railBadge.classList.remove("mui-rail-badge--ok", "mui-rail-badge--warn", "mui-rail-badge--fail", "mui-rail-badge--off");
      railBadge.classList.add(railCls);
    }
    if (railSub) railSub.textContent = text ? "severity: " + text : "health overview";
  }

  function bindReadinessSync() {
    var badge = $("manage-og-readiness-badge");
    if (!badge) return;
    var obs = new MutationObserver(syncReadinessPill);
    obs.observe(badge, { childList: true, characterData: true, subtree: true });
    syncReadinessPill();
  }

  // -------------------------------------------------------------------------
  // Inline action result chips, tied to button clicks.
  // -------------------------------------------------------------------------
  function activeSectionChip() {
    var deck = document.querySelector("[data-mui-deck]");
    var active = deck && deck.querySelector(".mui-deck-section.is-active");
    return active && active.querySelector(".mui-inline-result");
  }

  /**
   * Show "running" feedback immediately; upgrade to "done" success after
   * `timeoutMs` if nothing else has overwritten the chip in the meantime.
   * Handles silently-succeeding actions whose existing JS doesn't toast.
   */
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

  // Mirror banner text into both the header chip and the active section's chip.
  function bindResultMirror() {
    function watch(elId, kind) {
      var el = $(elId);
      if (!el) return;
      var last = "";
      var obs = new MutationObserver(function () {
        var text = (el.textContent || "").trim();
        if (text && text !== last) {
          last = text;
          var header = $("manage-og-header-result");
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
    watch("manage-og-banner", "error");
    watch("manage-og-success", "success");
  }

  // -------------------------------------------------------------------------
  // Init
  // -------------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", function () {
    watchAndTag("manage-og-provider-select");
    watchAndTag("manage-og-model-select");
    watchAndTag("manage-og-route-select");
    bindReadinessSync();
    bindResultMirror();

    // Header reload — silently re-fetches data; give visible feedback.
    bindFeedback("manage-og-refresh", ["manage-og-header-result"], "Reloading…", "Reloaded", 1500);

    // Provider actions.
    bindFeedback("manage-og-provider-test", ["manage-og-provider-result"], "Testing connection…", "Test finished", 4000);
    bindFeedback("manage-og-provider-update", ["manage-og-provider-result"], "Saving provider…", "Saved", 2200);
    bindFeedback("manage-og-provider-create", ["manage-og-provider-result"], "Creating provider…", "Created", 2200);

    // Model actions.
    bindFeedback("manage-og-model-test", ["manage-og-model-result"], "Testing model…", "Test finished", 4000);
    bindFeedback("manage-og-model-update", ["manage-og-model-result"], "Saving model…", "Saved", 2200);
    bindFeedback("manage-og-model-create", ["manage-og-model-result"], "Creating model…", "Created", 2200);
    bindFeedback("manage-og-model-delete", ["manage-og-model-result"], "Deleting model…", "Deleted", 2200);

    // Route actions.
    bindFeedback("manage-og-route-update", ["manage-og-route-result"], "Saving route…", "Saved", 2200);
    bindFeedback("manage-og-route-create", ["manage-og-route-result"], "Creating route…", "Created", 2200);

    // Runtime modes (header save).
    bindFeedback("manage-og-save-modes", ["manage-og-header-result"], "Saving runtime modes…", "Saved", 2200);
    bindFeedback("manage-og-bootstrap-reload", ["manage-og-header-result"], "Rebuilding config…", "Rebuilt", 2200);
  });
})();
