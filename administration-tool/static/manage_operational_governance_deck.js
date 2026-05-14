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
  function bindInlineResult(btnId, resultId, runningText) {
    var btn = $(btnId);
    var out = $(resultId);
    if (!btn || !out) return;
    btn.addEventListener("click", function () {
      ManageUI.setInlineResult(out, "info", runningText || "Running…");
    });
  }

  // Watch banners for transitions to surface as inline result on the active section.
  function bindResultMirror() {
    function currentSectionResult() {
      var deck = document.querySelector("[data-mui-deck]");
      if (!deck) return null;
      var active = deck.querySelector(".mui-deck-section.is-active");
      if (!active) return null;
      return active.querySelector(".mui-inline-result");
    }
    function watch(elId, kind) {
      var el = $(elId);
      if (!el) return;
      var last = "";
      var obs = new MutationObserver(function () {
        var text = (el.textContent || "").trim();
        if (text && text !== last) {
          var out = currentSectionResult();
          if (out) ManageUI.setInlineResult(out, kind, text);
          last = text;
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

    bindInlineResult("manage-og-provider-test", "manage-og-provider-result", "Testing connection…");
    bindInlineResult("manage-og-provider-update", "manage-og-provider-result", "Saving provider…");
    bindInlineResult("manage-og-provider-create", "manage-og-provider-result", "Creating provider…");
    bindInlineResult("manage-og-model-test", "manage-og-model-result", "Testing model…");
    bindInlineResult("manage-og-model-update", "manage-og-model-result", "Saving model…");
    bindInlineResult("manage-og-model-create", "manage-og-model-result", "Creating model…");
    bindInlineResult("manage-og-model-delete", "manage-og-model-result", "Deleting model…");
    bindInlineResult("manage-og-route-update", "manage-og-route-result", "Saving route…");
    bindInlineResult("manage-og-route-create", "manage-og-route-result", "Creating route…");
  });
})();
