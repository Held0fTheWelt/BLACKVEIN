/**
 * Operator-deck overlay for Runtime Dashboard.
 * Header chip feedback + banner mirror only — no pill extraction.
 */
(function () {
  "use strict";
  if (!window.ManageUI) return;
  function $(id) { return document.getElementById(id); }

  function activeSectionChip() {
    var deck = document.querySelector("[data-mui-deck]");
    var active = deck && deck.querySelector(".mui-deck-section.is-active");
    return active && active.querySelector(".mui-inline-result");
  }

  function bindFeedback(btnId, chipIds, runningText, doneText, timeoutMs) {
    var btn = $(btnId); if (!btn) return;
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
      var el = $(elId); if (!el) return;
      var last = "";
      var obs = new MutationObserver(function () {
        var text = (el.textContent || "").trim();
        if (text && text !== last) {
          last = text;
          var header = $("manage-rd-header-result");
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
    watch("manage-rd-banner", "error");
    watch("manage-rd-success", "success");
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindBannerMirror();
    bindFeedback("manage-rd-refresh", ["manage-rd-header-result"], "Reloading…", "Reloaded", 1500);
  });
})();
