(function () {
  "use strict";

  var selectedRunId = null;

  function renderButtons(hostId, items, onClick) {
    var host = document.getElementById(hostId);
    if (!host) return;
    host.innerHTML = "";
    if (!items.length) {
      host.textContent = "No items.";
      return;
    }
    items.forEach(function (row) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "ui-btn ui-btn-ghost ui-list-btn";
      btn.textContent = row.label;
      btn.addEventListener("click", function () {
        onClick(row.id);
      });
      host.appendChild(btn);
    });
  }

  function loadRuns() {
    return WorldEngineUI.apiFetch("admin/world-engine/runs").then(function (data) {
      var items = (data.items || []).map(function (run) {
        var id = run.id || run.run_id;
        return { id: id, label: id + " | " + (run.status || "") };
      });
      renderButtons("ui-runs-list", items, function (runId) {
        selectedRunId = runId;
        WorldEngineUI.apiFetch("admin/world-engine/runs/" + encodeURIComponent(runId))
          .then(function (detail) {
            WorldEngineUI.renderJson("ui-run-detail", detail);
          })
          .catch(function (err) {
            WorldEngineUI.setBanner("ui-page-banner", err.message, true);
          });
      });
    });
  }

  function loadSessionDetail(sessionId) {
    if (!sessionId) return;
    Promise.all([
      WorldEngineUI.apiFetch("admin/world-engine/story/sessions/" + encodeURIComponent(sessionId) + "/state"),
      WorldEngineUI.apiFetch("admin/world-engine/story/sessions/" + encodeURIComponent(sessionId) + "/diagnostics"),
    ])
      .then(function (parts) {
        WorldEngineUI.renderJson("ui-session-detail", { state: parts[0], diagnostics: parts[1] });
      })
      .catch(function (err) {
        WorldEngineUI.setBanner("ui-page-banner", err.message, true);
      });
  }

  function loadSessions() {
    return WorldEngineUI.apiFetch("admin/world-engine/story/sessions").then(function (data) {
      var items = (data.items || []).map(function (row) {
        return {
          id: row.session_id,
          label: row.session_id + " | " + (row.module_id || "") + " | turn " + String(row.turn_counter || 0),
        };
      });
      renderButtons("ui-sessions-list", items, function (sessionId) {
        WorldEngineSession.setSelectedSessionId(sessionId);
        loadSessionDetail(sessionId);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    WorldEngineSession.bindSessionPicker(loadSessionDetail);
    WorldEngineSession.loadSessionOptions();
    Promise.all([loadRuns(), loadSessions()]).catch(function (err) {
      WorldEngineUI.setBanner("ui-page-banner", err.message || String(err), true);
    });
  });
})();
