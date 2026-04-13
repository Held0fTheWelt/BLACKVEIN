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

  function renderNarrativeLists(payload) {
    var headline = document.getElementById("wecc-headline");
    var sub = document.getElementById("wecc-sub-lines");
    var dive = document.getElementById("wecc-deep-dive");
    var ctrlUl = document.getElementById("wecc-operator-controls");
    var summary = payload.operator_summary || {};
    if (headline) {
      headline.textContent = summary.headline || (payload.status && payload.status.control_plane_ok
        ? "Control plane reports no blocking issues."
        : "Review blockers and connectivity below.");
    }
    if (sub) {
      sub.innerHTML = "";
      (summary.sub_lines || []).forEach(function (line) {
        var li = document.createElement("li");
        li.textContent = line;
        sub.appendChild(li);
      });
    }
    if (dive) {
      dive.textContent = (summary.deep_dive_hint || "").replace(/\*\*/g, "");
    }
    if (ctrlUl) {
      ctrlUl.innerHTML = "";
      (payload.operator_controls || []).forEach(function (c) {
        var li = document.createElement("li");
        var label = c.label || c.id || "control";
        var method = c.method || "?";
        var path = c.path || "";
        li.textContent = label + " — " + method + " " + path;
        ctrlUl.appendChild(li);
      });
    }
  }

  function renderBlockersWarnings(payload) {
    var blockers = payload.blockers || [];
    var warnings = payload.warnings || [];
    var bEl = document.getElementById("wecc-blockers");
    var wEl = document.getElementById("wecc-warnings");
    if (bEl && blockers.length) {
      var lines = blockers.map(function (b) {
        var line = (b.message || b.code || "").trim();
        if (b.suggested_action) line += " Action: " + String(b.suggested_action).replace(/\*\*/g, "");
        return line;
      });
      bEl.textContent = JSON.stringify(lines, null, 2);
    } else if (bEl) {
      bEl.textContent = JSON.stringify(blockers, null, 2);
    }
    if (wEl && warnings.length) {
      var wlines = warnings.map(function (w) {
        var line = (w.message || w.code || "").trim();
        if (w.suggested_action) line += " Action: " + String(w.suggested_action).replace(/\*\*/g, "");
        return line;
      });
      wEl.textContent = JSON.stringify(wlines, null, 2);
    } else if (wEl) {
      wEl.textContent = JSON.stringify(warnings, null, 2);
    }
  }

  function loadControlCenter() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/world-engine/control-center")
      .then(function (payload) {
        renderNarrativeLists(payload);
        setJson("wecc-desired", payload.desired_play_service_state || {});
        setJson("wecc-observed", payload.observed_play_service_state || {});
        setJson("wecc-connectivity", payload.connectivity || {});
        setJson("wecc-summary", payload.active_runtime || {});
        renderBlockersWarnings(payload);
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
