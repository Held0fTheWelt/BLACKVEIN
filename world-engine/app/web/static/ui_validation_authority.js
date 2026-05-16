(function () {
  "use strict";

  function load(sessionId) {
    var q = sessionId ? { session_id: sessionId } : {};
    var api = WorldEngineUI;
    Promise.all([
      api.apiFetch(api.buildUrl("admin/governance/adr0041-authority-state", q)),
      api.apiFetch(api.buildUrl("admin/governance/runtime-readiness-authority", q)),
      api.apiFetch(api.buildUrl("admin/governance/capability-matrix", q)),
    ])
      .then(function (parts) {
        api.renderJson("ui-val-adr", parts[0]);
        api.renderJson("ui-val-readiness", parts[1]);
        api.renderJson("ui-val-matrix", parts[2]);
        api.setBanner("ui-page-banner", "", false);
      })
      .catch(function (err) {
        api.setBanner("ui-page-banner", err.message || String(err), true);
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    WorldEngineSession.bindSessionPicker(load);
    WorldEngineSession.loadSessionOptions();
    load(WorldEngineSession.selectedSessionId());
  });
})();
