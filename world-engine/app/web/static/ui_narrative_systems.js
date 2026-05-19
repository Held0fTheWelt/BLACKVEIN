(function () {
  "use strict";

  function load(sessionId) {
    var params = sessionId ? { session_id: sessionId } : {};
    Promise.all([
      WorldEngineUI.apiFetch("admin/narrative/runtime/gov-summary"),
      WorldEngineUI.apiFetch(WorldEngineUI.buildUrl("admin/governance/narrative-systems", params)),
    ])
      .then(function (parts) {
        WorldEngineUI.renderJson("ui-narr-gov", parts[0]);
        WorldEngineUI.renderJson("ui-narr-systems", parts[1]);
      })
      .catch(function (err) {
        WorldEngineUI.setBanner("ui-page-banner", err.message || String(err), true);
      });

    if (!sessionId) {
      WorldEngineUI.renderJson("ui-narr-thin-path", {
        note: "Select a session to load thin-path diagnostics.",
      });
      return;
    }

    WorldEngineUI.apiFetch(
      "admin/world-engine/story/sessions/" +
        encodeURIComponent(sessionId) +
        "/thin-path-summary?limit=20"
    )
      .then(function (summary) {
        WorldEngineUI.renderJson("ui-narr-thin-path", summary);
      })
      .catch(function (err) {
        WorldEngineUI.renderJson("ui-narr-thin-path", {
          error: err.message || String(err),
        });
        WorldEngineUI.setBanner("ui-page-banner", err.message || String(err), true);
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    WorldEngineSession.bindSessionPicker(load);
    WorldEngineSession.loadSessionOptions();
    load(WorldEngineSession.selectedSessionId());
  });
})();
