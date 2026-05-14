/**
 * manage_play_service_control_deck.js
 *
 * Operator-deck overlay for Play-Service control.
 *
 * Responsibilities:
 *   - Parse the rendered observed-state text and lift values into the
 *     sticky header pills (mode / health / readiness).
 *   - Classify pill colors based on the value.
 *   - Inline action chips + banner mirror.
 */
(function () {
  "use strict";
  if (!window.ManageUI) return;

  function $(id) { return document.getElementById(id); }

  function extractField(text, key) {
    var re = new RegExp("(?:^|\\n)\\s*" + key + ":\\s*([^\\n]+)");
    var m = (text || "").match(re);
    return m ? m[1].trim() : "";
  }

  function classifyPill(pillEl, value, okWords, warnWords) {
    if (!pillEl) return;
    pillEl.classList.remove("mui-pill--ok", "mui-pill--warn", "mui-pill--fail");
    var v = (value || "").toLowerCase();
    if (okWords && okWords.some(function (w) { return v.indexOf(w) > -1; })) {
      pillEl.classList.add("mui-pill--ok");
    } else if (warnWords && warnWords.some(function (w) { return v.indexOf(w) > -1; })) {
      pillEl.classList.add("mui-pill--warn");
    }
  }

  function syncObserved() {
    var observed = $("manage-psc-observed");
    if (!observed) return;
    var text = observed.textContent || "";
    var mode = extractField(text, "effective_mode");
    var health = extractField(text, "health");
    var readiness = extractField(text, "readiness");

    var modeVal = $("manage-psc-pill-mode-value");
    var healthVal = $("manage-psc-pill-health-value");
    var readyVal = $("manage-psc-pill-readiness-value");
    if (modeVal && mode) modeVal.textContent = mode;
    if (healthVal && health) healthVal.textContent = health;
    if (readyVal && readiness) readyVal.textContent = readiness;

    classifyPill($("manage-psc-pill-mode"), mode, ["docker", "local", "remote"], ["disabled"]);
    classifyPill($("manage-psc-pill-health"), health, ["ok", "healthy", "ready"], ["degraded", "unknown"]);
    classifyPill($("manage-psc-pill-readiness"), readiness, ["ready"], ["pending", "starting"]);

    // Secret + key presence pills (existing JS writes the label "present (environment)" or "not set").
    function presencePill(pillId, valueId) {
      var pill = $(pillId);
      var valueEl = $(valueId);
      if (!pill || !valueEl) return;
      var t = (valueEl.textContent || "").toLowerCase();
      pill.classList.remove("mui-pill--ok", "mui-pill--warn", "mui-pill--fail");
      if (t.indexOf("present") > -1) pill.classList.add("mui-pill--ok");
      else if (t.indexOf("not set") > -1 || t.indexOf("missing") > -1) pill.classList.add("mui-pill--warn");
    }
    presencePill("manage-psc-pill-secret", "manage-psc-secret-present");
    presencePill("manage-psc-pill-key", "manage-psc-key-present");
  }

  function bindObservedSync() {
    var observed = $("manage-psc-observed");
    if (observed) {
      var obs = new MutationObserver(syncObserved);
      obs.observe(observed, { childList: true, characterData: true, subtree: true });
    }
    // also watch the secret/key cells which exist outside the observed block
    ["manage-psc-secret-present", "manage-psc-key-present"].forEach(function (id) {
      var el = $(id);
      if (!el) return;
      var obs2 = new MutationObserver(syncObserved);
      obs2.observe(el, { childList: true, characterData: true, subtree: true });
    });
    syncObserved();
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
          var header = $("manage-psc-header-result");
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
    watch("manage-psc-banner", "error");
    watch("manage-psc-success", "success");
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindObservedSync();
    bindBannerMirror();
    bindFeedback("manage-psc-refresh", ["manage-psc-header-result"], "Reloading…", "Reloaded", 1500);
    bindFeedback("manage-psc-save", ["manage-psc-desired-result"], "Saving…", "Saved", 2200);
    bindFeedback("manage-psc-test", ["manage-psc-desired-result"], "Testing…", "Test finished", 4000);
    bindFeedback("manage-psc-apply", ["manage-psc-desired-result"], "Applying…", "Applied", 4000);
  });
})();
