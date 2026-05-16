(function () {
  "use strict";

  function load() {
    var api = window.WorldEngineUI;
    if (!api) return;
    api.setBanner("ui-page-banner", "Loading runtime dashboard...", false);
    var jobs = [
      api.apiFetch("admin/world-engine/health").then(function (d) {
        api.renderJson("ui-dash-health", d);
      }),
      api.apiFetch("admin/world-engine/story/sessions").then(function (d) {
        api.renderJson("ui-dash-sessions", d);
      }),
      api.apiFetch("admin/world-engine/runs").then(function (d) {
        api.renderJson("ui-dash-runs", d);
      }),
    ];
    var caps = window.__UI_CAPABILITIES__ || {};
    if (caps.ai_governance) {
      jobs.push(
        api.apiFetch("admin/governance/runtime-readiness-authority").then(function (d) {
          api.renderJson("ui-dash-readiness", d);
        })
      );
    } else {
      api.renderJson("ui-dash-readiness", { note: "Requires manage.ai_runtime_governance feature." });
    }
    Promise.all(jobs)
      .then(function () {
        api.setBanner("ui-page-banner", "", false);
      })
      .catch(function (err) {
        api.setBanner("ui-page-banner", err.message || String(err), true);
      });
  }

  document.addEventListener("DOMContentLoaded", load);
})();
