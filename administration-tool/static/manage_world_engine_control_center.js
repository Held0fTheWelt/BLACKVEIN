(function () {
  function showMessage(kind, message) {
    var err = document.getElementById("wecc-banner");
    var ok = document.getElementById("wecc-success");
    if (err) {
      err.style.display = "none";
      err.textContent = "";
    }
    if (ok) {
      ok.style.display = "none";
      ok.textContent = "";
    }
    if (!message) return;
    if (kind === "ok" && ok) {
      ok.style.display = "";
      ok.textContent = message;
      return;
    }
    if (err) {
      err.style.display = "";
      err.textContent = message;
    }
  }

  function setJson(id, payload) {
    var node = document.getElementById(id);
    if (!node) return;
    node.textContent = JSON.stringify(payload || {}, null, 2);
  }

  function loadControlCenter() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/world-engine/control-center")
      .then(function (payload) {
        setJson("wecc-desired", payload.desired_play_service_state || {});
        setJson("wecc-observed", payload.observed_play_service_state || {});
        setJson("wecc-connectivity", payload.connectivity || {});
        setJson("wecc-summary", payload.active_runtime || {});
        setJson("wecc-blockers", payload.blockers || []);
        setJson("wecc-warnings", payload.warnings || []);
      });
  }

  function postAction(path, successMessage) {
    return window.ManageAuth.apiFetchWithAuth(path, { method: "POST", body: "{}" })
      .then(function () {
        showMessage("ok", successMessage);
        return loadControlCenter();
      })
      .catch(function (err) {
        showMessage("err", err && err.message ? err.message : "Request failed");
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.ManageAuth) return;

    window.ManageAuth.ensureAuth()
      .then(function () {
        return loadControlCenter();
      })
      .catch(function (err) {
        showMessage("err", err && err.message ? err.message : "Failed to load control center");
      });

    var refreshBtn = document.getElementById("wecc-refresh");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        showMessage(null, "");
        loadControlCenter().catch(function (err) {
          showMessage("err", err && err.message ? err.message : "Refresh failed");
        });
      });
    }

    var testBtn = document.getElementById("wecc-test");
    if (testBtn) {
      testBtn.addEventListener("click", function () {
        showMessage(null, "");
        postAction("/api/v1/admin/play-service-control/test", "Play-service test completed.");
      });
    }

    var applyBtn = document.getElementById("wecc-apply");
    if (applyBtn) {
      applyBtn.addEventListener("click", function () {
        showMessage(null, "");
        postAction("/api/v1/admin/play-service-control/apply", "Desired play-service state applied.");
      });
    }
  });
})();
