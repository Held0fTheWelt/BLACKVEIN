(function () {
  "use strict";

  function writeJson(targetId, payload) {
    var node = document.getElementById(targetId);
    if (node) node.textContent = JSON.stringify(payload, null, 2);
  }

  document.addEventListener("DOMContentLoaded", function () {
    fetch("/api/health")
      .then(function (res) {
        return res.json();
      })
      .then(function (json) {
        writeJson("runtime-health", json);
      });
    fetch("/api/health/ready")
      .then(function (res) {
        return res.json();
      })
      .then(function (json) {
        writeJson("runtime-ready", json);
      });
    var caps = window.__UI_CAPABILITIES__ || {};
    if (caps.observe && window.WorldEngineUI) {
      WorldEngineUI.apiFetch("admin/world-engine/health")
        .then(function (data) {
          writeJson("ui-health-backend", data);
        })
        .catch(function (err) {
          writeJson("ui-health-backend", { error: err.message });
        });
    }
  });
})();
