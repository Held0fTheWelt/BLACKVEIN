/**
 * Canonical Inspector Suite workbench (read-only rendering).
 */
(function () {
  function byId(id) {
    return document.getElementById(id);
  }

  function setText(id, text) {
    var el = byId(id);
    if (!el) return;
    el.textContent = text == null ? "" : String(text);
  }

  function toPretty(value) {
    return JSON.stringify(value == null ? null : value, null, 2);
  }

  function statusText(section) {
    if (!section || typeof section !== "object") return "unavailable";
    return String(section.status || "unavailable");
  }

  function extractData(section) {
    if (!section || typeof section !== "object") return null;
    return section.data == null ? null : section.data;
  }

  function toPairs(data) {
    if (!data || typeof data !== "object") return [];
    return Object.keys(data).map(function (key) {
      return { key: key, value: data[key] };
    });
  }

  function renderKeyValueGrid(containerId, data, fallback) {
    var el = byId(containerId);
    if (!el) return;
    if (!data || typeof data !== "object") {
      el.innerHTML = '<p class="manage-empty">' + (fallback || "No data loaded.") + "</p>";
      return;
    }
    var rows = toPairs(data).map(function (row) {
      return (
        '<div class="inspector-kv-item">' +
        '<span class="inspector-kv-key">' +
        row.key +
        "</span>" +
        '<span class="inspector-kv-value">' +
        String(row.value == null ? "null" : row.value) +
        "</span>" +
        "</div>"
      );
    });
    el.innerHTML = rows.join("");
  }

  function renderMermaid(decisionTrace) {
    var host = byId("inspector-mermaid-host");
    if (!host) return;
    var data = extractData(decisionTrace);
    if (!data || !Array.isArray(data.flow_nodes) || !data.flow_nodes.length) {
      host.innerHTML = '<p class="manage-empty">No flow nodes available.</p>';
      return;
    }
    var nodes = data.flow_nodes.map(function (id) {
      var safeId = String(id).replace(/[^a-zA-Z0-9_]/g, "_");
      return safeId + '["' + String(id).replace(/"/g, '\\"') + '"]';
    });
    var edges = [];
    if (Array.isArray(data.flow_edges)) {
      edges = data.flow_edges
        .map(function (edge) {
          if (!edge || typeof edge !== "object") return "";
          var src = String(edge.from || "").replace(/[^a-zA-Z0-9_]/g, "_");
          var dst = String(edge.to || "").replace(/[^a-zA-Z0-9_]/g, "_");
          if (!src || !dst) return "";
          return src + " --> " + dst;
        })
        .filter(Boolean);
    }
    var graphSrc = ["flowchart LR"].concat(nodes).concat(edges).join("\n");
    if (!window.mermaid || typeof window.mermaid.render !== "function") {
      host.innerHTML = '<pre class="code-block">' + graphSrc + "</pre>";
      return;
    }
    window.mermaid
      .render("inspectorWorkbenchMermaidGraph", graphSrc)
      .then(function (result) {
        host.innerHTML = result.svg;
      })
      .catch(function () {
        host.innerHTML = '<pre class="code-block">' + graphSrc + "</pre>";
      });
  }

  function renderTurnPayload(payload) {
    var turnIdentity = payload.turn_identity || {};
    var decisionTrace = payload.decision_trace_projection || {};
    var authority = payload.authority_projection || {};
    var planner = payload.planner_state_projection || {};
    var gate = payload.gate_projection || {};
    var validation = payload.validation_projection || {};
    var fallback = payload.fallback_projection || {};

    var decisionData = extractData(decisionTrace) || {};
    var identityData = extractData(turnIdentity) || {};
    renderKeyValueGrid(
      "inspector-decision-summary",
      {
        projection_status: payload.projection_status,
        turn_identity_status: statusText(turnIdentity),
        decision_trace_status: statusText(decisionTrace),
        turn_number_world_engine: identityData.turn_number_world_engine,
        execution_health: decisionData.execution_health,
        fallback_path_taken: decisionData.fallback_path_taken,
      },
      "No decision summary loaded."
    );

    renderKeyValueGrid(
      "inspector-authority-boundary",
      extractData(authority),
      "No authority projection loaded."
    );
    setText("inspector-planner-state", toPretty(planner));
    setText("inspector-gate-outcome", toPretty(gate));
    setText("inspector-validation-outcome", toPretty(validation));
    setText("inspector-fallback-status", toPretty(fallback));
    setText("inspector-raw-json", toPretty(payload));

    var gateData = extractData(gate) || {};
    var rejection = {
      gate_status: statusText(gate),
      dominant_rejection_category: gateData.dominant_rejection_category,
      rejection_codes: gateData.rejection_codes,
      legacy_fallback_used: gateData.legacy_fallback_used,
      scene_function_mismatch_score: gateData.scene_function_mismatch_score,
      character_implausibility_score: gateData.character_implausibility_score,
      continuity_pressure_score: gateData.continuity_pressure_score,
      fluency_risk_score: gateData.fluency_risk_score,
    };
    setText("inspector-rejection-analysis", toPretty(rejection));
    renderMermaid(decisionTrace);
  }

  function switchTab(targetPanelId) {
    var tabs = document.querySelectorAll(".inspector-tab");
    var panels = document.querySelectorAll("[data-inspector-panel]");
    for (var i = 0; i < tabs.length; i++) {
      var tab = tabs[i];
      var active = tab.getAttribute("data-panel") === targetPanelId;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    }
    for (var j = 0; j < panels.length; j++) {
      var panel = panels[j];
      panel.hidden = panel.id !== targetPanelId;
    }
  }

  function initTabs() {
    var tabs = document.querySelectorAll(".inspector-tab");
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].addEventListener("click", function (event) {
        var panelId = event.currentTarget.getAttribute("data-panel");
        if (panelId) switchTab(panelId);
      });
    }
  }

  function initMermaid() {
    if (!window.mermaid || typeof window.mermaid.initialize !== "function") return;
    window.mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: "default",
    });
  }

  function buildPath(sessionId, mode, view) {
    var suffix = "/api/v1/admin/ai-stack/inspector/" + view + "/" + encodeURIComponent(sessionId);
    if (view === "turn" || view === "provenance-raw") {
      suffix += "?mode=" + encodeURIComponent(mode === "raw" ? "raw" : "canonical");
    }
    return suffix;
  }

  function loadWorkbench() {
    var sessionField = byId("inspector-session-id");
    var modeField = byId("inspector-mode");
    var sessionId = ((sessionField && sessionField.value) || "").trim();
    var mode = ((modeField && modeField.value) || "canonical").trim();
    if (!sessionId) {
      setText("inspector-load-state", "Bitte zuerst eine Backend-Session-ID eingeben.");
      return;
    }
    setText("inspector-load-state", "Lade Workbench-Projektionen ...");

    var paths = {
      turn: buildPath(sessionId, mode, "turn"),
      timeline: buildPath(sessionId, mode, "timeline"),
      comparison: buildPath(sessionId, mode, "comparison"),
      coverage: buildPath(sessionId, mode, "coverage-health"),
      provenance: buildPath(sessionId, mode, "provenance-raw"),
    };

    Promise.all([
      window.ManageAuth.apiFetchWithAuth(paths.turn),
      window.ManageAuth.apiFetchWithAuth(paths.timeline),
      window.ManageAuth.apiFetchWithAuth(paths.comparison),
      window.ManageAuth.apiFetchWithAuth(paths.coverage),
      window.ManageAuth.apiFetchWithAuth(paths.provenance),
    ])
      .then(function (payloads) {
        renderTurnPayload(payloads[0] || {});
        setText("inspector-timeline-json", toPretty(payloads[1] || {}));
        setText("inspector-comparison-json", toPretty(payloads[2] || {}));
        setText("inspector-coverage-json", toPretty(payloads[3] || {}));
        setText("inspector-provenance-json", toPretty(payloads[4] || {}));
        setText("inspector-load-state", "Workbench-Projektionen geladen.");
        switchTab("inspector-panel-turn");
      })
      .catch(function (error) {
        var msg = error && error.message ? error.message : "Request failed";
        setText("inspector-load-state", msg);
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.ManageAuth) return;
    initTabs();
    initMermaid();
    var loadBtn = byId("inspector-load-all");
    if (loadBtn) {
      loadBtn.addEventListener("click", loadWorkbench);
    }
    window.ManageAuth.ensureAuth().catch(function () {});
  });
})();
