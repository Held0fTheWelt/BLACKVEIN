/**
 * manage_ui.js — Reusable UI primitives for the admin tool.
 *
 * Public API on window.ManageUI:
 *   toast(kind, message, opts?)       — bottom-right sticky notification
 *   jsonViewer(target, data?, opts?)  — copy/wrap toolbar over a <pre>
 *   bindStatusElement(el)             — legacy banners fire toasts on text change
 *   bindRail(railEl)                  — mirror a hidden <select> into a clickable list
 *   bindDeck(deckEl)                  — section nav: clicking rail item shows matching inspector card
 *   bindDirtyForm(formEl, onSave, onDiscard) — track unsaved changes, expose count
 *
 * The module auto-binds on DOMContentLoaded:
 *   - any element matching [role="status"], [role="alert"], .form-error, .manage-state--ok,
 *     .form-success, or [data-status-toast]                      -> bindStatusElement
 *   - any <pre> with class .manage-psc-json or attribute data-json-viewer
 *                                                                -> jsonViewer
 *   - any [data-mui-rail]                                        -> bindRail
 *   - any [data-mui-deck]                                        -> bindDeck
 *   - any [data-mui-dirty-form]                                  -> bindDirtyForm
 */
(function () {
  "use strict";

  var ManageUI = (window.ManageUI = window.ManageUI || {});

  // ---------------------------------------------------------------------------
  // Toast
  // ---------------------------------------------------------------------------
  var toastRoot = null;

  function ensureToastRoot() {
    if (toastRoot && toastRoot.isConnected) return toastRoot;
    toastRoot = document.createElement("div");
    toastRoot.className = "mui-toasts";
    toastRoot.setAttribute("role", "region");
    toastRoot.setAttribute("aria-label", "Notifications");
    toastRoot.setAttribute("aria-live", "polite");
    document.body.appendChild(toastRoot);
    return toastRoot;
  }

  var KIND_LABELS = { success: "OK", ok: "OK", error: "Error", err: "Error", warn: "Warning", warning: "Warning", info: "Info" };
  function normalizeKind(kind) {
    if (kind === "ok") return "success";
    if (kind === "err") return "error";
    if (kind === "warning") return "warn";
    return kind || "info";
  }

  ManageUI.toast = function (kind, message, opts) {
    if (!message) return null;
    opts = opts || {};
    var root = ensureToastRoot();
    var nKind = normalizeKind(kind);
    var toast = document.createElement("div");
    toast.className = "mui-toast mui-toast--" + nKind;
    toast.setAttribute("role", nKind === "error" ? "alert" : "status");

    var accent = document.createElement("span");
    accent.className = "mui-toast-accent";
    accent.setAttribute("aria-hidden", "true");
    toast.appendChild(accent);

    var body = document.createElement("div");
    body.className = "mui-toast-body";
    var label = document.createElement("p");
    label.className = "mui-toast-kind";
    label.textContent = KIND_LABELS[nKind] || "Info";
    body.appendChild(label);
    var msg = document.createElement("p");
    msg.className = "mui-toast-msg";
    msg.textContent = String(message);
    body.appendChild(msg);
    toast.appendChild(body);

    var close = document.createElement("button");
    close.type = "button";
    close.className = "mui-toast-close";
    close.setAttribute("aria-label", "Dismiss notification");
    close.innerHTML = "&times;";
    toast.appendChild(close);

    var ttl = typeof opts.ttl === "number" ? opts.ttl : (nKind === "error" ? 8000 : 4500);
    var timer = null;
    var disposed = false;

    function dismiss() {
      if (disposed) return;
      disposed = true;
      if (timer) clearTimeout(timer);
      toast.classList.remove("mui-toast--in");
      toast.classList.add("mui-toast--out");
      window.setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 380);
    }
    function startTimer() {
      if (ttl <= 0) return;
      timer = window.setTimeout(dismiss, ttl);
    }
    close.addEventListener("click", dismiss);
    toast.addEventListener("mouseenter", function () { if (timer) clearTimeout(timer); timer = null; });
    toast.addEventListener("mouseleave", startTimer);

    root.appendChild(toast);
    window.requestAnimationFrame(function () { toast.classList.add("mui-toast--in"); });
    startTimer();
    return { dismiss: dismiss };
  };

  // ---------------------------------------------------------------------------
  // Status-element auto-binding (legacy banners -> toasts)
  // ---------------------------------------------------------------------------
  function detectStatusKind(el) {
    if (el.dataset && el.dataset.toastKind) return el.dataset.toastKind;
    if (el.classList.contains("form-error")) return "error";
    if (el.classList.contains("manage-state--ok")) return "success";
    if (el.classList.contains("form-success")) return "success";
    if (el.getAttribute && el.getAttribute("role") === "alert") return "error";
    return "info";
  }

  ManageUI.bindStatusElement = function (el) {
    if (!el || el.__muiStatusBound) return;
    el.__muiStatusBound = true;
    var lastText = (el.textContent || "").trim();
    var hideOriginal = el.dataset.toastReplace !== "false";

    var observer = new MutationObserver(function () {
      var text = (el.textContent || "").trim();
      if (text && text !== lastText) {
        ManageUI.toast(detectStatusKind(el), text);
        if (hideOriginal) {
          el.hidden = true;
          el.style.display = "none";
        }
      } else if (!text) {
        // cleared — do nothing
      }
      lastText = text;
    });
    observer.observe(el, { childList: true, characterData: true, subtree: true });
    // Force-hide on bind if already non-empty? No — initial render is from the page, not an event.
  };

  function autoBindStatusElements(root) {
    var selectors = [
      "[data-status-toast]",
      ".form-error[role=\"status\"]",
      ".form-error[role=\"alert\"]",
      ".manage-state.manage-state--ok[role=\"status\"]",
      ".form-success[role=\"status\"]"
    ];
    var seen = new WeakSet();
    selectors.forEach(function (sel) {
      (root || document).querySelectorAll(sel).forEach(function (el) {
        if (seen.has(el)) return;
        seen.add(el);
        ManageUI.bindStatusElement(el);
      });
    });
  }

  // ---------------------------------------------------------------------------
  // JSON Viewer
  // ---------------------------------------------------------------------------
  function escapeHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function syntaxHighlight(text) {
    var escaped = escapeHtml(text);
    return escaped.replace(
      /("(?:\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(?:true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      function (match, _full, colon) {
        var cls = "mui-json-num";
        if (/^"/.test(match)) {
          cls = colon ? "mui-json-key" : "mui-json-string";
        } else if (match === "true" || match === "false") {
          cls = "mui-json-bool";
        } else if (match === "null") {
          cls = "mui-json-null";
        }
        return "<span class=\"" + cls + "\">" + match + "</span>";
      }
    );
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      try {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "absolute";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        var ok = document.execCommand("copy");
        document.body.removeChild(ta);
        ok ? resolve() : reject(new Error("execCommand returned false"));
      } catch (err) {
        reject(err);
      }
    });
  }

  function wrapJsonPre(pre, opts) {
    if (pre.__muiJsonHost) return pre.__muiJsonHost;
    opts = opts || {};
    var host = document.createElement("div");
    host.className = "mui-json";
    pre.parentNode.insertBefore(host, pre);
    host.appendChild(pre);
    pre.classList.add("mui-json-pre");
    pre.__muiJsonHost = host;

    var bar = document.createElement("div");
    bar.className = "mui-json-bar";
    var label = document.createElement("span");
    label.className = "mui-json-label";
    label.textContent = opts.label || pre.dataset.jsonLabel || "JSON";
    bar.appendChild(label);
    var actions = document.createElement("div");
    actions.className = "mui-json-actions";

    var wrapBtn = document.createElement("button");
    wrapBtn.type = "button";
    wrapBtn.className = "mui-json-btn";
    wrapBtn.dataset.action = "wrap";
    wrapBtn.setAttribute("aria-pressed", "true");
    wrapBtn.textContent = "Wrap";
    actions.appendChild(wrapBtn);

    var copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "mui-json-btn";
    copyBtn.dataset.action = "copy";
    copyBtn.textContent = "Copy";
    actions.appendChild(copyBtn);

    bar.appendChild(actions);
    host.insertBefore(bar, pre);

    wrapBtn.addEventListener("click", function () {
      var nowrap = pre.classList.toggle("mui-json-pre--nowrap");
      wrapBtn.setAttribute("aria-pressed", nowrap ? "false" : "true");
    });

    copyBtn.addEventListener("click", function () {
      var raw = pre.__muiRaw != null ? pre.__muiRaw : (pre.textContent || "");
      copyToClipboard(raw).then(function () {
        copyBtn.textContent = "Copied";
        copyBtn.classList.add("is-success");
        window.setTimeout(function () {
          copyBtn.textContent = "Copy";
          copyBtn.classList.remove("is-success");
        }, 1500);
      }).catch(function (err) {
        ManageUI.toast("error", "Copy failed: " + (err && err.message ? err.message : err));
      });
    });

    // Observe external textContent writes (page code sets pre.textContent = JSON.stringify(...))
    // and re-render with syntax highlighting.
    var observer = new MutationObserver(function () {
      if (pre.__muiRendering) return;
      var txt = (pre.textContent || "").trim();
      var raw = pre.__muiRaw == null ? null : pre.__muiRaw.trim();
      if (txt && txt !== raw) {
        renderJsonContent(pre, pre.textContent);
      }
    });
    observer.observe(pre, { childList: true, characterData: true, subtree: true });
    pre.__muiObserver = observer;

    return host;
  }

  function renderJsonContent(pre, raw) {
    if (raw == null) raw = "";
    pre.__muiRaw = raw;
    pre.__muiRendering = true;
    var trimmed = String(raw).trim();
    if (!trimmed || trimmed === "{}" || trimmed === "[]") {
      pre.innerHTML = "<span class=\"mui-json-empty\">No data.</span>";
    } else {
      // Try to pretty-print if it parses; otherwise show as-is.
      try {
        var parsed = JSON.parse(trimmed);
        var pretty = JSON.stringify(parsed, null, 2);
        pre.__muiRaw = pretty;
        pre.innerHTML = syntaxHighlight(pretty);
      } catch (_e) {
        pre.innerHTML = syntaxHighlight(String(raw));
      }
    }
    pre.__muiRendering = false;
  }

  ManageUI.jsonViewer = function (target, data, opts) {
    var pre = typeof target === "string" ? document.querySelector(target) : target;
    if (!pre || pre.tagName !== "PRE") return null;
    wrapJsonPre(pre, opts || {});
    if (data !== undefined) {
      var raw = typeof data === "string" ? data : JSON.stringify(data, null, 2);
      renderJsonContent(pre, raw);
    } else if ((pre.textContent || "").trim()) {
      renderJsonContent(pre, pre.textContent);
    }
    return pre.__muiJsonHost;
  };

  function autoBindJsonViewers(root) {
    var pres = (root || document).querySelectorAll(
      "pre.manage-psc-json, pre[data-json-viewer]"
    );
    pres.forEach(function (pre) {
      var labelGuess = pre.dataset.jsonLabel;
      if (!labelGuess) {
        var summary = pre.parentElement && pre.parentElement.tagName === "DETAILS"
          ? pre.parentElement.querySelector("summary")
          : null;
        if (summary) labelGuess = (summary.textContent || "").trim();
      }
      ManageUI.jsonViewer(pre, undefined, { label: labelGuess || "JSON" });
    });
  }

  // ---------------------------------------------------------------------------
  // Rail (hidden <select> -> rich clickable list)
  // ---------------------------------------------------------------------------
  function buildRailItem(option, opts) {
    var li = document.createElement("li");
    li.className = "mui-rail-item";
    li.dataset.value = option.value;
    if (!option.value) li.classList.add("mui-rail-item--empty");

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "mui-rail-btn";
    btn.dataset.value = option.value;

    var badge = document.createElement("span");
    badge.className = "mui-rail-badge";
    badge.setAttribute("aria-hidden", "true");
    var badgeKind = option.dataset && option.dataset.muiBadge;
    if (badgeKind) {
      badge.classList.add("mui-rail-badge--" + badgeKind);
    }
    btn.appendChild(badge);

    var labelWrap = document.createElement("span");
    labelWrap.className = "mui-rail-label";
    var raw = option.textContent || option.value || "(unnamed)";
    var primary = raw;
    var secondary = "";
    var pipeIdx = raw.indexOf(" · ");
    if (pipeIdx > -1) {
      primary = raw.slice(0, pipeIdx);
      secondary = raw.slice(pipeIdx + 3);
    }
    var primaryEl = document.createElement("span");
    primaryEl.className = "mui-rail-primary";
    primaryEl.textContent = primary;
    labelWrap.appendChild(primaryEl);
    if (secondary) {
      var secondaryEl = document.createElement("span");
      secondaryEl.className = "mui-rail-secondary";
      secondaryEl.textContent = secondary;
      labelWrap.appendChild(secondaryEl);
    }
    btn.appendChild(labelWrap);
    li.appendChild(btn);

    btn.addEventListener("click", function () {
      var select = document.getElementById(opts.sourceId);
      if (!select) return;
      select.value = option.value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      // If the rail container points at a deck section, navigate the deck too.
      if (opts.deckTarget) {
        var deckEl = opts.railEl && opts.railEl.closest("[data-mui-deck]");
        if (deckEl) {
          activateDeck(deckEl, opts.deckTarget);
          if (history && history.replaceState) {
            history.replaceState(null, "", "#" + opts.deckTarget);
          }
        }
      }
    });

    return li;
  }

  function renderRail(railEl, sourceId) {
    var select = document.getElementById(sourceId);
    if (!select) return;
    var list = railEl.querySelector(".mui-rail-list");
    if (!list) {
      list = document.createElement("ul");
      list.className = "mui-rail-list";
      // Place list after the head/filter row if present, otherwise append.
      var insertAfter = railEl.querySelector(".mui-rail-filter-row, .mui-rail-group-head");
      if (insertAfter && insertAfter.nextSibling) {
        railEl.insertBefore(list, insertAfter.nextSibling);
      } else if (insertAfter) {
        railEl.appendChild(list);
      } else {
        railEl.appendChild(list);
      }
    }
    var deckTarget = railEl.dataset.deckTarget || null;
    list.innerHTML = "";
    Array.prototype.forEach.call(select.options, function (option) {
      if (!option.value) return; // skip placeholder "Select…"
      var li = buildRailItem(option, { sourceId: sourceId, deckTarget: deckTarget, railEl: railEl });
      list.appendChild(li);
    });
    updateRailActive(railEl, sourceId);

    // Update count badge if present
    var countEl = railEl.querySelector("[data-mui-rail-count]");
    if (countEl) countEl.textContent = String(list.children.length);

    if (!list.children.length) {
      var empty = document.createElement("li");
      empty.className = "mui-rail-empty";
      empty.textContent = railEl.dataset.muiRailEmpty || "Nothing yet.";
      list.appendChild(empty);
    }
  }

  function updateRailActive(railEl, sourceId) {
    var select = document.getElementById(sourceId);
    if (!select) return;
    var current = select.value;
    railEl.querySelectorAll(".mui-rail-btn").forEach(function (btn) {
      var match = btn.dataset.value === current && !!current;
      btn.classList.toggle("is-active", match);
      btn.setAttribute("aria-pressed", match ? "true" : "false");
    });
  }

  ManageUI.bindRail = function (railEl) {
    if (!railEl || railEl.__muiRailBound) return;
    var sourceId = railEl.dataset.muiRail;
    if (!sourceId) return;
    railEl.__muiRailBound = true;

    var select = document.getElementById(sourceId);
    if (!select) return;
    select.classList.add("mui-rail-source");

    // Optional filter input
    var filter = railEl.querySelector("[data-mui-rail-filter]");
    var filterValue = "";
    if (filter) {
      filter.addEventListener("input", function () {
        filterValue = (filter.value || "").toLowerCase().trim();
        railEl.querySelectorAll(".mui-rail-item").forEach(function (li) {
          var hay = (li.textContent || "").toLowerCase();
          li.style.display = !filterValue || hay.indexOf(filterValue) > -1 ? "" : "none";
        });
      });
    }

    renderRail(railEl, sourceId);

    var observer = new MutationObserver(function () { renderRail(railEl, sourceId); });
    observer.observe(select, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["data-mui-badge", "value"]
    });

    select.addEventListener("change", function () { updateRailActive(railEl, sourceId); });
  };

  function autoBindRails(root) {
    (root || document).querySelectorAll("[data-mui-rail]").forEach(ManageUI.bindRail);
  }

  // ---------------------------------------------------------------------------
  // Deck (section nav inside a page)
  // ---------------------------------------------------------------------------
  function activateDeck(deckEl, target) {
    if (!deckEl || !target) return;
    var navLinks = deckEl.querySelectorAll("[data-deck-target]");
    var sections = deckEl.querySelectorAll("[data-deck-section]");
    navLinks.forEach(function (a) {
      var match = a.dataset.deckTarget === target;
      a.classList.toggle("is-active", match);
      if (match) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    });
    sections.forEach(function (sec) {
      sec.classList.toggle("is-active", sec.dataset.deckSection === target);
    });
  }

  ManageUI.deckActivate = function (deckOrTarget, target) {
    var deckEl;
    if (target === undefined) {
      // Single-arg: find the first deck
      deckEl = document.querySelector("[data-mui-deck]");
      target = deckOrTarget;
    } else if (typeof deckOrTarget === "string") {
      deckEl = document.querySelector(deckOrTarget);
    } else {
      deckEl = deckOrTarget;
    }
    activateDeck(deckEl, target);
  };

  ManageUI.bindDeck = function (deckEl) {
    if (!deckEl || deckEl.__muiDeckBound) return;
    deckEl.__muiDeckBound = true;

    deckEl.addEventListener("click", function (ev) {
      var trigger = ev.target.closest("[data-deck-target]");
      if (!trigger || !deckEl.contains(trigger)) return;
      // Don't intercept rail-item buttons — they handle deck activation themselves
      // after also setting the select value.
      if (trigger.classList.contains("mui-rail-btn")) return;
      ev.preventDefault();
      var target = trigger.dataset.deckTarget;
      activateDeck(deckEl, target);
      if (history && history.replaceState) {
        history.replaceState(null, "", "#" + target);
      }
    });

    // Honor URL hash on load.
    var hash = (location.hash || "").replace(/^#/, "");
    var firstNav = deckEl.querySelector("[data-deck-target]");
    if (hash && deckEl.querySelector("[data-deck-section=\"" + CSS.escape(hash) + "\"]")) {
      activateDeck(deckEl, hash);
    } else if (firstNav) {
      activateDeck(deckEl, firstNav.dataset.deckTarget);
    }
  };

  function autoBindDecks(root) {
    (root || document).querySelectorAll("[data-mui-deck]").forEach(ManageUI.bindDeck);
  }

  // ---------------------------------------------------------------------------
  // Dirty-form tracker
  // ---------------------------------------------------------------------------
  function snapshotForm(formEl) {
    var snap = {};
    formEl.querySelectorAll("input, select, textarea").forEach(function (el) {
      if (!el.name && !el.id) return;
      var key = el.id || el.name;
      if (el.type === "checkbox" || el.type === "radio") {
        snap[key] = !!el.checked;
      } else {
        snap[key] = el.value || "";
      }
    });
    return snap;
  }

  function diffSnapshot(a, b) {
    var changed = 0;
    Object.keys(b).forEach(function (k) {
      if (a[k] !== b[k]) changed++;
    });
    return changed;
  }

  ManageUI.bindDirtyForm = function (formEl, opts) {
    if (!formEl || formEl.__muiDirtyBound) return;
    formEl.__muiDirtyBound = true;
    opts = opts || {};
    var counterEl = opts.counter || formEl.querySelector("[data-dirty-count]");
    var saveBtn = opts.saveBtn || formEl.querySelector("[data-dirty-save]");
    var discardBtn = opts.discardBtn || formEl.querySelector("[data-dirty-discard]");

    var baseline = snapshotForm(formEl);

    function recompute() {
      var current = snapshotForm(formEl);
      var n = diffSnapshot(baseline, current);
      formEl.classList.toggle("is-dirty", n > 0);
      if (counterEl) counterEl.textContent = n ? String(n) : "";
      if (saveBtn) saveBtn.disabled = n === 0;
      if (discardBtn) discardBtn.hidden = n === 0;
    }
    formEl.addEventListener("input", recompute);
    formEl.addEventListener("change", recompute);

    ManageUI.resetDirtyForm = function (target) {
      var form = target || formEl;
      baseline = snapshotForm(form);
      recompute();
    };

    if (discardBtn) {
      discardBtn.addEventListener("click", function () {
        // Restore baseline.
        Object.keys(baseline).forEach(function (k) {
          var el = document.getElementById(k) || formEl.querySelector("[name=\"" + k + "\"]");
          if (!el) return;
          if (el.type === "checkbox" || el.type === "radio") el.checked = !!baseline[k];
          else el.value = baseline[k];
        });
        recompute();
      });
    }
    recompute();
  };

  function autoBindDirtyForms(root) {
    (root || document).querySelectorAll("[data-mui-dirty-form]").forEach(function (formEl) {
      ManageUI.bindDirtyForm(formEl);
    });
  }

  // ---------------------------------------------------------------------------
  // Inline action result (text appears next to a button after action)
  // ---------------------------------------------------------------------------
  ManageUI.setInlineResult = function (target, kind, message) {
    var el = typeof target === "string" ? document.querySelector(target) : target;
    if (!el) return;
    var nKind = normalizeKind(kind);
    el.className = "mui-inline-result mui-inline-result--" + nKind;
    el.textContent = message || "";
    el.hidden = !message;
  };

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  function init() {
    autoBindStatusElements(document);
    autoBindJsonViewers(document);
    autoBindRails(document);
    autoBindDecks(document);
    autoBindDirtyForms(document);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Re-scan when callers add new content dynamically.
  ManageUI.scan = function (root) {
    autoBindStatusElements(root);
    autoBindJsonViewers(root);
    autoBindRails(root);
    autoBindDecks(root);
    autoBindDirtyForms(root);
  };
})();
