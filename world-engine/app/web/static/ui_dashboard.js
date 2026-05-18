(function () {
  "use strict";

  function view() {
    return window.WorldEngineDiagnosticView;
  }

  function load() {
    var api = window.WorldEngineUI;
    var dx = view();
    if (!api || !dx) return;

    api.setBanner("ui-page-banner", "Loading runtime dashboard…", false);

    var jobs = [
      api.apiFetch("admin/world-engine/control-center").then(function (payload) {
        dx.renderControlCenter(payload || {});
      }),
    ];

    var caps = window.__UI_CAPABILITIES__ || {};
    if (caps.ai_governance) {
      jobs.push(
        api.apiFetch("admin/governance/runtime-readiness-authority").then(function (payload) {
          dx.renderReadinessAuthority(payload || {});
        })
      );
    } else {
      var section = document.getElementById("ui-dash-readiness-section");
      if (section) section.hidden = true;
      dx.renderJsonPre("ui-dash-audit-readiness", {
        note: "Requires manage.ai_runtime_governance feature.",
      });
    }

    Promise.all(jobs)
      .then(function () {
        api.setBanner("ui-page-banner", "", false);
      })
      .catch(function (err) {
        api.setBanner("ui-page-banner", err.message || String(err), true);
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    load();
    var refresh = document.getElementById("ui-dash-refresh");
    if (refresh) {
      refresh.addEventListener("click", load);
    }
  });
})();
