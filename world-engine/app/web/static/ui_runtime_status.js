(function () {
  function writeJson(targetId, payload) {
    var node = document.getElementById(targetId);
    if (!node) return;
    node.textContent = JSON.stringify(payload, null, 2);
  }

  function writeError(targetId, message) {
    var node = document.getElementById(targetId);
    if (!node) return;
    node.textContent = message;
  }

  function loadStatus() {
    fetch("/api/health")
      .then(function (res) {
        return res.json();
      })
      .then(function (json) {
        writeJson("runtime-health", json);
      })
      .catch(function () {
        writeError("runtime-health", "Failed to load /api/health.");
      });

    fetch("/api/health/ready")
      .then(function (res) {
        return res.json();
      })
      .then(function (json) {
        writeJson("runtime-ready", json);
      })
      .catch(function () {
        writeError("runtime-ready", "Failed to load /api/health/ready.");
      });
  }

  document.addEventListener("DOMContentLoaded", loadStatus);
})();
