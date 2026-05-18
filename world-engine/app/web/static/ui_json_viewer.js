/**
 * World-Engine UI — JSON viewer (copy / wrap toolbar), aligned with administration-tool ManageUI.jsonViewer.
 *
 * Auto-binds: pre.ui-code, pre.code-block, pre[data-json-viewer]
 * Patches WorldEngineUI.renderJson when ui_api.js is loaded.
 */
(function () {
  "use strict";

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function syntaxHighlight(text) {
    var escaped = escapeHtml(text);
    return escaped.replace(
      /("(?:\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(?:true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      function (match, _full, colon) {
        var cls = "ui-json-num";
        if (/^"/.test(match)) {
          cls = colon ? "ui-json-key" : "ui-json-string";
        } else if (match === "true" || match === "false") {
          cls = "ui-json-bool";
        } else if (match === "null") {
          cls = "ui-json-null";
        }
        return '<span class="' + cls + '">' + match + "</span>";
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

  function labelFromContext(pre) {
    if (pre.dataset && pre.dataset.jsonLabel) {
      return pre.dataset.jsonLabel.trim();
    }
    var labelled = pre.getAttribute("aria-label");
    if (labelled && labelled.trim()) {
      return labelled.trim();
    }
    var card = pre.closest(".ui-card");
    if (card) {
      var heading = card.querySelector("h2, h3");
      if (heading && heading.textContent) {
        return heading.textContent.trim();
      }
    }
    return "JSON";
  }

  function wrapJsonPre(pre, opts) {
    if (pre.__uiJsonHost) {
      return pre.__uiJsonHost;
    }
    opts = opts || {};
    var host = document.createElement("div");
    host.className = "ui-json";
    pre.parentNode.insertBefore(host, pre);
    host.appendChild(pre);
    if (pre.classList.contains("ui-code")) {
      pre.classList.remove("ui-code");
    }
    pre.classList.add("ui-json-pre");
    pre.__uiJsonHost = host;

    var bar = document.createElement("div");
    bar.className = "ui-json-bar";
    var label = document.createElement("span");
    label.className = "ui-json-label";
    label.textContent = opts.label || labelFromContext(pre);
    bar.appendChild(label);

    var actions = document.createElement("div");
    actions.className = "ui-json-actions";

    var wrapBtn = document.createElement("button");
    wrapBtn.type = "button";
    wrapBtn.className = "ui-json-btn";
    wrapBtn.dataset.action = "wrap";
    wrapBtn.setAttribute("aria-pressed", "true");
    wrapBtn.textContent = "Wrap";
    actions.appendChild(wrapBtn);

    var copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "ui-json-btn";
    copyBtn.dataset.action = "copy";
    copyBtn.textContent = "Copy";
    actions.appendChild(copyBtn);

    bar.appendChild(actions);
    host.insertBefore(bar, pre);

    wrapBtn.addEventListener("click", function () {
      var nowrap = pre.classList.toggle("ui-json-pre--nowrap");
      wrapBtn.setAttribute("aria-pressed", nowrap ? "false" : "true");
    });

    copyBtn.addEventListener("click", function () {
      var raw = pre.__uiRaw != null ? pre.__uiRaw : pre.textContent || "";
      copyToClipboard(raw)
        .then(function () {
          copyBtn.textContent = "Copied";
          copyBtn.classList.add("is-success");
          window.setTimeout(function () {
            copyBtn.textContent = "Copy";
            copyBtn.classList.remove("is-success");
          }, 1500);
        })
        .catch(function () {
          copyBtn.textContent = "Failed";
          window.setTimeout(function () {
            copyBtn.textContent = "Copy";
          }, 1500);
        });
    });

    var observer = new MutationObserver(function () {
      if (pre.__uiRendering) {
        return;
      }
      var txt = (pre.textContent || "").trim();
      var raw = pre.__uiRaw == null ? null : String(pre.__uiRaw).trim();
      if (txt && txt !== raw) {
        renderJsonContent(pre, pre.textContent);
      }
    });
    observer.observe(pre, { childList: true, characterData: true, subtree: true });
    pre.__uiObserver = observer;

    return host;
  }

  function renderJsonContent(pre, raw) {
    if (raw == null) {
      raw = "";
    }
    pre.__uiRaw = raw;
    pre.__uiRendering = true;
    var trimmed = String(raw).trim();
    if (!trimmed || trimmed === "{}" || trimmed === "[]") {
      pre.innerHTML = '<span class="ui-json-empty">No data.</span>';
    } else {
      try {
        var parsed = JSON.parse(trimmed);
        var pretty = JSON.stringify(parsed, null, 2);
        pre.__uiRaw = pretty;
        pre.innerHTML = syntaxHighlight(pretty);
      } catch (_e) {
        pre.innerHTML = syntaxHighlight(String(raw));
      }
    }
    pre.__uiRendering = false;
  }

  function jsonViewer(target, data, opts) {
    var pre = typeof target === "string" ? document.getElementById(target) : target;
    if (!pre || pre.tagName !== "PRE") {
      return null;
    }
    wrapJsonPre(pre, opts || {});
    if (data !== undefined) {
      var raw = typeof data === "string" ? data : JSON.stringify(data, null, 2);
      renderJsonContent(pre, raw);
    } else if ((pre.textContent || "").trim()) {
      renderJsonContent(pre, pre.textContent);
    }
    return pre.__uiJsonHost;
  }

  function autoBindJsonViewers(root) {
    var pres = (root || document).querySelectorAll(
      "pre.ui-code, pre.code-block, pre[data-json-viewer]"
    );
    pres.forEach(function (pre) {
      jsonViewer(pre, undefined, { label: labelFromContext(pre) });
    });
  }

  function installWorldEngineUi() {
    window.WorldEngineUI = window.WorldEngineUI || {};
    window.WorldEngineUI.jsonViewer = jsonViewer;
    window.WorldEngineUI.renderJson = function (targetId, payload, opts) {
      var node = document.getElementById(targetId);
      if (!node) {
        return;
      }
      var merged = opts || {};
      if (!merged.label) {
        merged.label = labelFromContext(node);
      }
      jsonViewer(node, payload, merged);
    };
  }

  installWorldEngineUi();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      autoBindJsonViewers(document);
    });
  } else {
    autoBindJsonViewers(document);
  }
})();
