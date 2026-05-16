(function () {
  "use strict";

  function load(sessionId) {
    var aspect = (document.getElementById("ui-ledger-aspect") || {}).value || "";
    var params = { session_id: sessionId };
    if (aspect) params.aspect = aspect;
    WorldEngineUI.apiFetch(WorldEngineUI.buildUrl("admin/governance/runtime-aspect-ledger", params))
      .then(function (data) {
        WorldEngineUI.renderJson("ui-ledger-view", data);
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
