/**
 * World-Engine UI: same-origin backend proxy client (/ui-api/*).
 */
(function () {
  "use strict";

  function formatError(body, status) {
    if (!body || typeof body !== "object") {
      return status ? "Request failed (HTTP " + status + ")" : "Request failed";
    }
    if (typeof body.message === "string" && body.message.trim()) {
      return body.message.trim();
    }
    if (typeof body.error === "string" && body.error.trim()) {
      return body.error.trim();
    }
    if (body.error && typeof body.error === "object" && body.error.message) {
      return String(body.error.message);
    }
    return status ? "Request failed (HTTP " + status + ")" : "Request failed";
  }

  function apiFetch(path, opts) {
    opts = opts || {};
    var method = (opts.method || "GET").toUpperCase();
    var url = path.indexOf("/ui-api/") === 0 ? path : "/ui-api/" + path.replace(/^\//, "");
    var headers = opts.headers || {};
    headers.Accept = headers.Accept || "application/json";
    if (method !== "GET" && method !== "HEAD") {
      headers["Content-Type"] = headers["Content-Type"] || "application/json";
    }
    return fetch(url, {
      method: method,
      headers: headers,
      body: opts.body != null ? opts.body : undefined,
      credentials: "same-origin",
    }).then(function (res) {
      return res.json().catch(function () {
        return {};
      }).then(function (body) {
        if (res.status === 401) {
          window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
          throw { status: 401, message: "Unauthorized" };
        }
        if (!res.ok) {
          throw { status: res.status, message: formatError(body, res.status), body: body };
        }
        if (body && typeof body === "object" && Object.prototype.hasOwnProperty.call(body, "ok") && body.ok === false) {
          throw { status: res.status, message: formatError(body, res.status), body: body };
        }
        if (body && typeof body === "object" && Object.prototype.hasOwnProperty.call(body, "data")) {
          return body.data;
        }
        return body;
      });
    });
  }

  function governanceData(payload) {
    if (payload && typeof payload === "object" && Object.prototype.hasOwnProperty.call(payload, "data")) {
      return payload.data;
    }
    return payload;
  }

  window.WorldEngineUI = {
    apiFetch: apiFetch,
    governanceData: governanceData,
    buildUrl: function (path, params) {
      var search = new URLSearchParams();
      Object.keys(params || {}).forEach(function (key) {
        var value = params[key];
        if (value != null && String(value).trim() !== "") {
          search.set(key, String(value).trim());
        }
      });
      var query = search.toString();
      return query ? path + "?" + query : path;
    },
    renderJson: function (targetId, payload) {
      var node = document.getElementById(targetId);
      if (!node) return;
      node.textContent = JSON.stringify(payload, null, 2);
    },
    setBanner: function (targetId, message, isError) {
      var el = document.getElementById(targetId);
      if (!el) return;
      if (!message) {
        el.hidden = true;
        el.textContent = "";
        el.className = "ui-banner";
        return;
      }
      el.hidden = false;
      el.textContent = message;
      el.className = isError ? "ui-banner ui-banner-error" : "ui-banner ui-banner-ok";
    },
  };
})();
