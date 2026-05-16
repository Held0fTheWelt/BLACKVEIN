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
  }

  document.addEventListener("DOMContentLoaded", function () {
    WorldEngineSession.bindSessionPicker(load);
    WorldEngineSession.loadSessionOptions();
    load(WorldEngineSession.selectedSessionId());
  });
})();
