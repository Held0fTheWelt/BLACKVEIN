(function () {
  "use strict";

  function loadSession(sessionId) {
    if (!sessionId) return;
    WorldEngineUI.apiFetch("admin/world-engine/story/sessions/" + encodeURIComponent(sessionId) + "/diagnostics")
      .then(function (diag) {
        WorldEngineUI.renderJson("ui-live-diagnostics", diag);
        var envelope =
          diag && diag.diagnostics_envelope
            ? diag.diagnostics_envelope
            : diag && diag.last_diagnostics_envelope
              ? diag.last_diagnostics_envelope
              : { note: "No diagnostics envelope in session diagnostics payload." };
        WorldEngineUI.renderJson("ui-live-envelope", envelope);
      })
      .catch(function (err) {
        WorldEngineUI.setBanner("ui-page-banner", err.message, true);
      });
    WorldEngineUI.apiFetch("admin/world-engine/story/sessions/" + encodeURIComponent(sessionId) + "/state")
      .then(function (state) {
        WorldEngineUI.renderJson("ui-live-state", state);
      })
      .catch(function (err) {
        WorldEngineUI.setBanner("ui-page-banner", err.message, true);
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    WorldEngineSession.bindSessionPicker(loadSession);
    WorldEngineSession.loadSessionOptions().then(function () {
      var sid = WorldEngineSession.selectedSessionId();
      if (sid) loadSession(sid);
    });
  });
})();
