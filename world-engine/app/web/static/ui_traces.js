(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    Promise.all([
      WorldEngineUI.apiFetch("admin/governance/evidence/langfuse-mcp"),
      WorldEngineUI.apiFetch("admin/observability/status").catch(function () {
        return { note: "Observability status requires admin feature or is unavailable." };
      }),
    ])
      .then(function (parts) {
        WorldEngineUI.renderJson("ui-trace-evidence", parts[0]);
        WorldEngineUI.renderJson("ui-trace-obs", parts[1]);
      })
      .catch(function (err) {
        WorldEngineUI.setBanner("ui-page-banner", err.message || String(err), true);
      });
  });
})();
