(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var shell = document.querySelector(".ui-shell");
    var toggle = document.getElementById("ui-side-toggle");
    var scrim = document.getElementById("ui-shell-scrim");
    var side = document.getElementById("ui-side");
    if (!shell || !toggle || !side) return;

    function setOpen(open) {
      shell.dataset.sideOpen = open ? "true" : "false";
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    }

    toggle.addEventListener("click", function () {
      setOpen(shell.dataset.sideOpen !== "true");
    });
    if (scrim) {
      scrim.addEventListener("click", function () {
        setOpen(false);
      });
    }
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && shell.dataset.sideOpen === "true") {
        setOpen(false);
        toggle.focus();
      }
    });
    side.addEventListener("click", function (event) {
      var link = event.target.closest("a.ui-nav-link");
      if (link && window.matchMedia("(max-width: 900px)").matches) {
        setOpen(false);
      }
    });

    var caps = window.__UI_CAPABILITIES__ || {};
    function capAllowed(need) {
      if (need === "observe") return !!caps.observe || !!caps.ai_governance;
      if (need === "ai_governance") return !!caps.ai_governance;
      if (need === "any_runtime") return !!caps.any_runtime;
      return !!caps[need];
    }
    document.querySelectorAll("[data-ui-cap]").forEach(function (el) {
      var need = el.getAttribute("data-ui-cap");
      if (!need) return;
      el.style.display = capAllowed(need) ? "" : "none";
    });
  });
})();
