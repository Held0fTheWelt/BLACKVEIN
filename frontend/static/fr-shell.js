/**
 * Frontend shell — sidebar toggle, scrim close, current-page highlight.
 * Mirrors the world-engine/admin shell pattern.
 */
(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
      return;
    }
    document.addEventListener("DOMContentLoaded", fn);
  }

  function highlightCurrent() {
    var current = (window.location.pathname || "/").replace(/\/+$/, "") || "/";
    var links = document.querySelectorAll(".fr-nav-link");
    var matchedLink = null;
    var matchedLength = -1;
    links.forEach(function (link) {
      var href = (link.getAttribute("href") || "").replace(/\/+$/, "") || "/";
      var isMatch = false;
      if (href === current) {
        isMatch = true;
      } else if (href !== "/" && current.indexOf(href + "/") === 0) {
        isMatch = true;
      }
      if (isMatch && href.length > matchedLength) {
        matchedLink = link;
        matchedLength = href.length;
      }
    });
    if (matchedLink) {
      matchedLink.classList.add("is-current");
      matchedLink.setAttribute("aria-current", "page");
      var group = matchedLink.closest(".fr-nav-group");
      if (group && !group.open) group.open = true;
    }
  }

  function wireSidebar() {
    var shell = document.querySelector(".fr-shell");
    var toggle = document.getElementById("fr-side-toggle");
    var scrim = document.getElementById("fr-shell-scrim");
    var side = document.getElementById("fr-side");
    if (!shell || !toggle) return;

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

    if (side) {
      side.addEventListener("click", function (event) {
        var link = event.target.closest("a.fr-nav-link");
        if (link && window.matchMedia("(max-width: 900px)").matches) {
          setOpen(false);
        }
      });
    }
  }

  ready(function () {
    highlightCurrent();
    wireSidebar();
  });
})();
