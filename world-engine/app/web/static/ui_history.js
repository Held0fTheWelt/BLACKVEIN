(function () {
  "use strict";

  function loadTimeline(sessionId) {
    if (!sessionId) return;
    WorldEngineUI.apiFetch("admin/world-engine/story/sessions/" + encodeURIComponent(sessionId) + "/diagnostics")
      .then(function (payload) {
        var events = payload && payload.diagnostics ? payload.diagnostics : payload;
        WorldEngineUI.renderJson("ui-history-timeline", events);
      })
      .catch(function (err) {
        WorldEngineUI.setBanner("ui-page-banner", err.message, true);
      });
  }

  function loadTranscript() {
    var runId = String((document.getElementById("ui-history-run-id") || {}).value || "").trim();
    if (!runId) return;
    WorldEngineUI.apiFetch("admin/world-engine/runs/" + encodeURIComponent(runId) + "/transcript")
      .then(function (data) {
        WorldEngineUI.renderJson("ui-history-transcript", data);
      })
      .catch(function (err) {
        WorldEngineUI.setBanner("ui-page-banner", err.message, true);
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    WorldEngineSession.bindSessionPicker(loadTimeline);
    WorldEngineSession.loadSessionOptions();
    var runInput = document.getElementById("ui-history-run-id");
    if (runInput) {
      runInput.addEventListener("change", loadTranscript);
    }
    loadTimeline(WorldEngineSession.selectedSessionId());
  });
})();
