/**
 * Canonical Inspector Suite workbench (read-only rendering).
 * Renders backend projections only — does not infer stage presence from missing nested JSON.
 */
(function () {
  var lastTurnPayload = null;
  var mermaidSeq = 0;

  function byId(id) {
    return document.getElementById(id);
  }

  function setText(id, text) {
    var el = byId(id);
    if (!el) return;
    el.textContent = text == null ? "" : String(text);
  }

  function setHtml(id, html) {
    var el = byId(id);
    if (!el) return;
    el.innerHTML = html;
  }

  function toPretty(value) {
    return JSON.stringify(value == null ? null : value, null, 2);
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatDisplayValue(v) {
    if (v == null) return "null";
    if (typeof v === "object") return JSON.stringify(v);
    return String(v);
  }

  function statusText(section) {
    if (!section || typeof section !== "object") return "unavailable";
    return String(section.status || "unavailable");
  }

  function extractData(section) {
    if (!section || typeof section !== "object") return null;
    return section.data == null ? null : section.data;
  }

  function sectionReason(section) {
    if (!section || typeof section !== "object") return "";
    return String(section.unavailable_reason || section.unsupported_reason || "");
  }

  function envelopeBanner(section) {
    if (!section || typeof section !== "object") {
      return '<p class="inspector-section-status inspector-section-status-unavailable">No projection envelope.</p>';
    }
    var st = statusText(section);
    var reason = sectionReason(section);
    var cls = "inspector-section-status";
    if (st === "unavailable") cls += " inspector-section-status-unavailable";
    else if (st === "unsupported") cls += " inspector-section-status-unsupported";
    else cls += " inspector-section-status-supported";
    var parts = ['<p class="' + cls + '"><strong>Status:</strong> ' + escapeHtml(st) + "</p>"];
    if (reason) {
      parts.push(
        '<p class="inspector-section-reason"><strong>Reason:</strong> ' + escapeHtml(reason) + "</p>"
      );
    }
    return parts.join("");
  }

  function toPairs(data) {
    if (!data || typeof data !== "object") return [];
    return Object.keys(data).map(function (key) {
      return { key: key, value: data[key] };
    });
  }

  function kvGridInnerHtml(data) {
    if (!data || typeof data !== "object") return '<p class="manage-empty">No data.</p>';
    return toPairs(data)
      .map(function (row) {
        return (
          '<div class="inspector-kv-item">' +
          '<span class="inspector-kv-key">' +
          escapeHtml(row.key) +
          "</span>" +
          '<span class="inspector-kv-value">' +
          escapeHtml(formatDisplayValue(row.value)) +
          "</span>" +
          "</div>"
        );
      })
      .join("");
  }

  function renderKeyValueGrid(containerId, data, fallback) {
    var el = byId(containerId);
    if (!el) return;
    if (!data || typeof data !== "object") {
      el.innerHTML = '<p class="manage-empty">' + (fallback || "No data loaded.") + "</p>";
      return;
    }
    el.innerHTML = kvGridInnerHtml(data);
  }

  function nextMermaidId() {
    mermaidSeq += 1;
    return "inspectorWorkbenchMermaid_" + mermaidSeq;
  }

  function renderMermaidSource(graphSrc, host) {
    if (!host) return;
    if (!graphSrc || !String(graphSrc).trim()) {
      host.innerHTML = '<p class="manage-empty">No diagram source from backend.</p>';
      return;
    }
    if (!window.mermaid || typeof window.mermaid.render !== "function") {
      host.innerHTML = '<pre class="code-block">' + escapeHtml(graphSrc) + "</pre>";
      return;
    }
    var graphId = nextMermaidId();
    window.mermaid
      .render(graphId, graphSrc)
      .then(function (result) {
        host.innerHTML = result.svg;
      })
      .catch(function () {
        host.innerHTML = '<pre class="code-block">' + escapeHtml(graphSrc) + "</pre>";
      });
  }

  /** Semantic flow: uses only backend `stages[].presence` — no client-side stage inference. */
  function buildSemanticMermaidGraph(semanticFlow) {
    if (!semanticFlow || !Array.isArray(semanticFlow.stages) || !semanticFlow.stages.length) {
      return "";
    }
    var lines = ["flowchart TB"];
    semanticFlow.stages.forEach(function (s) {
      if (!s || typeof s !== "object") return;
      var sid = String(s.id || "").replace(/[^a-zA-Z0-9_]/g, "_");
      if (!sid) return;
      var nodeId = "sem_" + sid;
      var label = String(s.label || s.id || "") + " [" + String(s.presence || "?") + "]";
      var safeLabel = label.replace(/"/g, "'").replace(/\]/g, ")");
      lines.push(nodeId + '["' + safeLabel + '"]');
    });
    (semanticFlow.edges || []).forEach(function (edge) {
      if (!edge || typeof edge !== "object") return;
      var a = "sem_" + String(edge.from_stage || "").replace(/[^a-zA-Z0-9_]/g, "_");
      var b = "sem_" + String(edge.to_stage || "").replace(/[^a-zA-Z0-9_]/g, "_");
      if (!a || !b || a === "sem_" || b === "sem_") return;
      lines.push(a + " --> " + b);
    });
    return lines.join("\n");
  }

  function buildGraphExecutionMermaid(graphExec) {
    if (!graphExec || !Array.isArray(graphExec.flow_nodes) || !graphExec.flow_nodes.length) {
      return "";
    }
    var nodes = graphExec.flow_nodes.map(function (id) {
      var safeId = String(id).replace(/[^a-zA-Z0-9_]/g, "_");
      return safeId + '["' + String(id).replace(/"/g, '\\"') + '"]';
    });
    var edges = [];
    if (Array.isArray(graphExec.flow_edges)) {
      edges = graphExec.flow_edges
        .map(function (edge) {
          if (!edge || typeof edge !== "object") return "";
          var src = String(edge.from || "").replace(/[^a-zA-Z0-9_]/g, "_");
          var dst = String(edge.to || "").replace(/[^a-zA-Z0-9_]/g, "_");
          if (!src || !dst) return "";
          return src + " --> " + dst;
        })
        .filter(Boolean);
    }
    return ["flowchart LR"].concat(nodes).concat(edges).join("\n");
  }

  function renderMermaidPanel(decisionTrace) {
    var host = byId("inspector-mermaid-host");
    if (!host) return;
    var data = extractData(decisionTrace) || {};
    var modeEl = byId("inspector-mermaid-mode");
    var mode = modeEl && modeEl.value === "graph_execution" ? "graph_execution" : "semantic";

    var semanticSrc = buildSemanticMermaidGraph(data.semantic_decision_flow);
    var graphSrc = buildGraphExecutionMermaid(data.graph_execution_flow);

    if (mode === "semantic") {
      if (semanticSrc) {
        renderMermaidSource(semanticSrc, host);
        return;
      }
      if (graphSrc) {
        host.innerHTML =
          '<p class="manage-empty">Semantic decision flow empty; showing graph execution fallback.</p>';
        renderMermaidSource(graphSrc, host);
        return;
      }
      host.innerHTML = '<p class="manage-empty">No semantic or graph execution flow from backend.</p>';
      return;
    }

    if (graphSrc) {
      renderMermaidSource(graphSrc, host);
      return;
    }
    host.innerHTML = '<p class="manage-empty">No graph execution flow nodes from backend.</p>';
  }

  function mergeSectionSummary(section) {
    var data = extractData(section);
    var base = { envelope_status: statusText(section) };
    if (sectionReason(section)) {
      base.envelope_reason = sectionReason(section);
    }
    if (data && typeof data === "object" && !Array.isArray(data)) {
      Object.keys(data).forEach(function (k) {
        base[k] = data[k];
      });
    } else if (data != null) {
      base.payload = data;
    }
    return base;
  }

  function renderPlannerStructured(plannerSection) {
    var host = byId("inspector-planner-structured");
    if (!host) return;
    var parts = [envelopeBanner(plannerSection)];
    var pdata = extractData(plannerSection);
    if (statusText(plannerSection) !== "supported" || !pdata || typeof pdata !== "object") {
      parts.push('<p class="manage-empty">No structured planner data.</p>');
      host.innerHTML = parts.join("");
      return;
    }

    function card(title, bodyHtml) {
      return (
        '<section class="inspector-planner-card"><h4>' +
        escapeHtml(title) +
        "</h4>" +
        bodyHtml +
        "</section>"
      );
    }

    if (pdata.support_posture && typeof pdata.support_posture === "object") {
      parts.push(card("Support posture (canonical resolver)", '<div class="inspector-kv-grid">' + kvGridInnerHtml(pdata.support_posture) + "</div>"));
    }

    var sections = [
      { key: "semantic_move_record", title: "SemanticMoveRecord" },
      { key: "social_state_record", title: "SocialStateRecord" },
      { key: "scene_plan_record", title: "ScenePlanRecord" },
    ];
    sections.forEach(function (spec) {
      var v = pdata[spec.key];
      if (v == null) {
        parts.push(card(spec.title, '<p class="manage-empty">null</p>'));
      } else if (typeof v === "object" && !Array.isArray(v)) {
        parts.push(card(spec.title, '<div class="inspector-kv-grid">' + kvGridInnerHtml(v) + "</div>"));
      } else {
        parts.push(card(spec.title, "<pre class=\"code-block\">" + escapeHtml(toPretty(v)) + "</pre>"));
      }
    });

    var minds = pdata.character_mind_records;
    if (minds == null) {
      parts.push(card("CharacterMindRecord collection", '<p class="manage-empty">null</p>'));
    } else if (Array.isArray(minds) && minds.length) {
      var rows = minds
        .map(function (m, i) {
          if (!m || typeof m !== "object") return "<tr><td colspan=\"3\">" + escapeHtml(String(m)) + "</td></tr>";
          return (
            "<tr><td>" +
            escapeHtml(String(i)) +
            "</td><td>" +
            escapeHtml(String(m.character_key != null ? m.character_key : "")) +
            "</td><td><pre class=\"code-block\">" +
            escapeHtml(toPretty(m)) +
            "</pre></td></tr>"
          );
        })
        .join("");
      parts.push(
        card(
          "CharacterMindRecord collection",
          '<table class="inspector-data-table"><thead><tr><th>#</th><th>character_key</th><th>record</th></tr></thead><tbody>' +
            rows +
            "</tbody></table>"
        )
      );
    } else {
      parts.push(card("CharacterMindRecord collection", '<p class="manage-empty">empty list</p>'));
    }

    parts.push(
      '<details class="inspector-json-details"><summary class="inspector-json-details-summary">Raw planner_state_projection.data (secondary)</summary><pre class="code-block">' +
        escapeHtml(toPretty(pdata)) +
        "</pre></details>"
    );

    host.innerHTML = parts.join("");
  }

  function renderGatePanels(gateSection) {
    var gdata = extractData(gateSection) || {};
    var legacy = gdata.legacy_compatibility_summary;

    renderKeyValueGrid(
      "inspector-gate-outcome-grid",
      {
        envelope_status: statusText(gateSection),
        envelope_reason: sectionReason(gateSection) || null,
        gate_result: gdata.gate_result,
        rejection_reasons: gdata.rejection_reasons,
        effect_rationale_codes: gdata.effect_rationale_codes,
        legacy_fallback_used: gdata.legacy_fallback_used,
      },
      "No gate projection loaded."
    );

    var posture = {};
    [
      "supports_scene_function",
      "continues_or_changes_pressure",
      "character_plausibility_posture",
      "continuity_support_posture",
      "empty_fluency_risk",
      "diagnostic_trace",
    ].forEach(function (k) {
      if (Object.prototype.hasOwnProperty.call(gdata, k)) posture[k] = gdata[k];
    });

    if (Object.keys(posture).length === 0) {
      renderKeyValueGrid(
        "inspector-gate-posture-grid",
        { _note: "No bounded posture fields present on gate payload." },
        "No gate posture loaded."
      );
    } else {
      renderKeyValueGrid("inspector-gate-posture-grid", posture, "No gate posture loaded.");
    }

    var leg = byId("inspector-gate-legacy-block");
    if (leg) {
      if (legacy && typeof legacy === "object" && Object.keys(legacy).length) {
        leg.innerHTML = kvGridInnerHtml(legacy);
      } else {
        leg.innerHTML = '<p class="manage-empty">No legacy compatibility fields.</p>';
      }
    }
  }

  function renderTurnPayload(payload) {
    lastTurnPayload = payload;
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
        schema_version: payload.schema_version,
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

    renderPlannerStructured(planner);
    renderGatePanels(gate);
    renderKeyValueGrid(
      "inspector-validation-outcome-grid",
      mergeSectionSummary(validation),
      "No validation projection loaded."
    );
    renderKeyValueGrid(
      "inspector-fallback-status-grid",
      mergeSectionSummary(fallback),
      "No fallback projection loaded."
    );
    setText("inspector-raw-json", toPretty(payload));

    renderMermaidPanel(decisionTrace);
  }

  function renderDistributionBlock(title, dist) {
    if (!dist || typeof dist !== "object" || !Object.keys(dist).length) {
      return (
        '<section class="inspector-dist-block"><h4 class="inspector-subheading">' +
        escapeHtml(title) +
        '</h4><p class="manage-empty">No distribution data.</p></section>'
      );
    }
    var rows = Object.keys(dist).map(function (k) {
      return { key: k, value: dist[k] };
    });
    var inner = rows
      .map(function (r) {
        return (
          '<div class="inspector-kv-item"><span class="inspector-kv-key">' +
          escapeHtml(r.key) +
          '</span><span class="inspector-kv-value">' +
          escapeHtml(formatDisplayValue(r.value)) +
          "</span></div>"
        );
      })
      .join("");
    return (
      '<section class="inspector-dist-block"><h4 class="inspector-subheading">' +
      escapeHtml(title) +
      '</h4><div class="inspector-kv-grid">' +
      inner +
      "</div></section>"
    );
  }

  function renderCoverageView(root) {
    var hostId = "inspector-coverage-structured";
    var section = root && root.coverage_health_projection;
    var html = envelopeBanner(section);
    var data = extractData(section) || {};
    var metrics = data.metrics || {};
    var dist = data.distribution || {};
    var fb = metrics.fallback_frequency;
    if (fb && typeof fb === "object") {
      html += '<section class="inspector-dist-block"><h4 class="inspector-subheading">Fallback frequency</h4><div class="inspector-kv-grid">';
      html += toPairs(fb)
        .map(function (r) {
          return (
            '<div class="inspector-kv-item"><span class="inspector-kv-key">' +
            escapeHtml(r.key) +
            '</span><span class="inspector-kv-value">' +
            escapeHtml(formatDisplayValue(r.value)) +
            "</span></div>"
          );
        })
        .join("");
      html += "</div></section>";
    }
    if (metrics.not_supported_gate_rate != null) {
      html +=
        '<p class="manage-state">not_supported gate rate: ' +
        escapeHtml(String(metrics.not_supported_gate_rate)) +
        "</p>";
    }
    html += renderDistributionBlock("Gate outcome distribution", dist.gate_outcome_distribution);
    html += renderDistributionBlock("Validation outcome distribution", dist.validation_outcome_distribution);
    html += renderDistributionBlock(
      "Effect and rejection rationale distribution",
      dist.effect_and_rejection_rationale_distribution
    );
    html += renderDistributionBlock("Empty fluency risk distribution", dist.empty_fluency_risk_distribution);
    html += renderDistributionBlock(
      "Character plausibility posture distribution",
      dist.character_plausibility_posture_distribution
    );
    html += renderDistributionBlock(
      "Continuity support posture distribution",
      dist.continuity_support_posture_distribution
    );
    html += renderDistributionBlock("Legacy fallback used distribution", dist.legacy_fallback_used_distribution);
    html += renderDistributionBlock(
      "Dramatic effect weak signal distribution",
      dist.dramatic_effect_weak_signal_distribution
    );
    html += renderDistributionBlock(
      "Semantic planner support level distribution",
      dist.semantic_planner_support_level_distribution
    );
    html += renderDistributionBlock(
      "Legacy dominant rejection category distribution",
      dist.legacy_dominant_rejection_category_distribution
    );
    html += renderDistributionBlock(
      "Unsupported / unavailable frequency",
      dist.unsupported_unavailable_frequency
    );
    if (metrics.total_turns != null) {
      html +=
        '<p class="manage-state">Total turns (metrics): ' + escapeHtml(String(metrics.total_turns)) + "</p>";
    }
    setHtml(hostId, html);
  }

  function renderProvenanceView(root) {
    var section = root && root.provenance_raw_projection;
    var parts = [envelopeBanner(section)];
    var data = extractData(section) || {};
    var entries = data.entries;
    if (statusText(section) === "supported" && Array.isArray(entries) && entries.length) {
      var colSet = {};
      entries.forEach(function (row) {
        if (row && typeof row === "object") {
          Object.keys(row).forEach(function (k) {
            colSet[k] = true;
          });
        }
      });
      var cols = Object.keys(colSet);
      var tableHtml =
        '<table class="inspector-data-table"><caption class="visually-hidden">Canonical provenance entries</caption><thead><tr>' +
        cols
          .map(function (c) {
            return "<th>" + escapeHtml(c) + "</th>";
          })
          .join("") +
        "</tr></thead><tbody>";
      tableHtml += entries
        .map(function (row) {
          return (
            "<tr>" +
            cols
              .map(function (c) {
                var v = row && typeof row === "object" ? row[c] : null;
                return "<td>" + escapeHtml(formatDisplayValue(v)) + "</td>";
              })
              .join("") +
            "</tr>"
          );
        })
        .join("");
      tableHtml += "</tbody></table>";
      parts.push(tableHtml);
      if (data.canonical_vs_raw_boundary) {
        parts.push(
          '<p class="manage-state inspector-boundary-note">' +
            escapeHtml(String(data.canonical_vs_raw_boundary)) +
            "</p>"
        );
      }
    } else {
      parts.push('<p class="manage-empty">No canonical provenance entries to display.</p>');
    }
    setHtml("inspector-provenance-canonical", parts.join(""));

    var rawEl = byId("inspector-provenance-raw-json");
    if (rawEl) {
      if (root && root.raw_mode_loaded && root.raw_evidence) {
        rawEl.textContent = toPretty(root.raw_evidence);
      } else {
        rawEl.textContent =
          "Raw evidence not loaded. Select read mode “raw” and load the workbench to inspect raw bundles (secondary material only).";
      }
    }
  }

  function renderTimelineViewFixed(root) {
    var host = byId("inspector-timeline-structured");
    if (!host) return;
    var section = root && root.timeline_projection;
    var parts = [envelopeBanner(section)];
    var st = statusText(section);
    var data = extractData(section);
    if (st === "supported" && data && Array.isArray(data.turns) && data.turns.length) {
      parts.push(
        '<p class="manage-state">Total turns: ' +
          escapeHtml(String(data.total_turns != null ? data.total_turns : data.turns.length)) +
          "</p>"
      );
      var cols = [
        { key: "turn_index", label: "Turn index" },
        { key: "turn_number", label: "Turn #" },
        { key: "trace_id", label: "Trace id" },
        { key: "semantic_planner_support_level", label: "Support level" },
        { key: "semantic_move_type", label: "Move type" },
        { key: "scene_risk_band", label: "Scene risk" },
        { key: "selected_scene_function", label: "Scene function" },
        { key: "gate_result", label: "Gate result" },
        { key: "empty_fluency_risk", label: "Empty fluency risk" },
        { key: "character_plausibility_posture", label: "Plausibility" },
        { key: "continuity_support_posture", label: "Continuity support" },
        { key: "continues_or_changes_pressure", label: "Continues/changes pressure" },
        { key: "supports_scene_function", label: "Supports scene fn" },
        { key: "legacy_fallback_used", label: "Legacy fallback" },
        { key: "accepted_weak_signal", label: "Weak-signal accept" },
        { key: "dramatic_effect_weak_signal", label: "Weak signal (validation)" },
        { key: "validation_status", label: "Validation" },
        { key: "validation_reason", label: "Validation reason" },
        { key: "fallback_path_taken", label: "Fallback path" },
        { key: "execution_health", label: "Execution health" },
        { key: "route_mode", label: "Route mode" },
        { key: "route_reason_code", label: "Route reason" },
        { key: "effect_rationale_codes", label: "Effect rationale codes" },
        { key: "gate_diagnostic_trace_codes", label: "Gate trace codes" },
      ];
      var tableHtml =
        '<div style="overflow-x:auto"><table class="inspector-data-table"><caption class="visually-hidden">Timeline turns</caption><thead><tr>' +
        cols
          .map(function (c) {
            return "<th>" + escapeHtml(c.label) + "</th>";
          })
          .join("") +
        "</tr></thead><tbody>";
      tableHtml += data.turns
        .map(function (row) {
          return (
            "<tr>" +
            cols
              .map(function (c) {
                var v = row[c.key];
                return "<td>" + escapeHtml(formatDisplayValue(v)) + "</td>";
              })
              .join("") +
            "</tr>"
          );
        })
        .join("");
      tableHtml += "</tbody></table></div>";
      parts.push(tableHtml);
    } else {
      parts.push('<p class="manage-empty">No structured timeline rows to display.</p>');
    }
    host.innerHTML = parts.join("");
  }

  function renderComparisonRowBlocks(row) {
    var blocks = [];
    var surface = row && row.visible_output_surface_comparison;
    if (surface && typeof surface === "object" && !Array.isArray(surface)) {
      blocks.push(
        '<section class="inspector-dist-block"><h4 class="inspector-subheading">Visible output surface comparison</h4><div class="inspector-kv-grid">' +
          kvGridInnerHtml(surface) +
          "</div></section>"
      );
    }
    var candidates = row && row.multi_pressure_candidates_to;
    if (Array.isArray(candidates)) {
      if (candidates.length) {
        blocks.push(
          '<section class="inspector-dist-block"><h4 class="inspector-subheading">Multi-pressure candidates (to turn)</h4><ul class="inspector-dim-list">' +
            candidates
              .map(function (candidate) {
                return "<li>" + escapeHtml(formatDisplayValue(candidate)) + "</li>";
              })
              .join("") +
            "</ul></section>"
        );
      } else {
        blocks.push(
          '<section class="inspector-dist-block"><h4 class="inspector-subheading">Multi-pressure candidates (to turn)</h4><p class="manage-empty">empty list</p></section>'
        );
      }
    }
    return blocks.join("");
  }

  function renderComparisonViewFixed(root) {
    var host = byId("inspector-comparison-structured");
    if (!host) return;
    var section = root && root.comparison_projection;
    var parts = [envelopeBanner(section)];
    var data = extractData(section) || {};
    if (data.semantic_planner_support_level != null || data.dramatic_effect_evaluator_class != null) {
      parts.push(
        '<p class="manage-state">Support level: ' +
          escapeHtml(String(data.semantic_planner_support_level)) +
          " · Evaluator: " +
          escapeHtml(String(data.dramatic_effect_evaluator_class)) +
          "</p>"
      );
    }
    if (data.mandatory_dimension != null) {
      parts.push(
        '<p class="manage-state">Mandatory dimension: <strong>' +
          escapeHtml(String(data.mandatory_dimension)) +
          "</strong></p>"
      );
    }
    if (Array.isArray(data.unsupported_dimensions) && data.unsupported_dimensions.length) {
      parts.push('<h4 class="inspector-subheading">Unsupported dimensions (explicit)</h4><ul class="inspector-dim-list">');
      data.unsupported_dimensions.forEach(function (d) {
        parts.push("<li>" + escapeHtml(String(d)) + "</li>");
      });
      parts.push("</ul>");
    }
    if (Array.isArray(data.supported_dimensions) && data.supported_dimensions.length) {
      parts.push('<h4 class="inspector-subheading">Supported dimensions</h4><ul class="inspector-dim-list">');
      data.supported_dimensions.forEach(function (d) {
        parts.push("<li>" + escapeHtml(String(d)) + "</li>");
      });
      parts.push("</ul>");
    }
    var comparisons = data.comparisons;
    if (statusText(section) === "supported" && Array.isArray(comparisons) && comparisons.length) {
      var cols = [
        { key: "from_turn_number", label: "From turn" },
        { key: "to_turn_number", label: "To turn" },
        { key: "from_trace_id", label: "Trace id (from)" },
        { key: "to_trace_id", label: "Trace id (to)" },
        { key: "gate_result_from", label: "Gate (from)" },
        { key: "gate_result_to", label: "Gate (to)" },
        { key: "empty_fluency_risk_from", label: "Fluency (from)" },
        { key: "empty_fluency_risk_to", label: "Fluency (to)" },
        { key: "character_plausibility_posture_from", label: "Plaus. (from)" },
        { key: "character_plausibility_posture_to", label: "Plaus. (to)" },
        { key: "continuity_support_posture_from", label: "Continuity (from)" },
        { key: "continuity_support_posture_to", label: "Continuity (to)" },
        { key: "legacy_fallback_used_from", label: "Legacy fb (from)" },
        { key: "legacy_fallback_used_to", label: "Legacy fb (to)" },
        { key: "semantic_move_type_from", label: "Move (from)" },
        { key: "semantic_move_type_to", label: "Move (to)" },
        { key: "scene_risk_band_from", label: "Risk (from)" },
        { key: "scene_risk_band_to", label: "Risk (to)" },
        { key: "validation_status_from", label: "Validation (from)" },
        { key: "validation_status_to", label: "Validation (to)" },
        { key: "fallback_path_taken_from", label: "Fallback (from)" },
        { key: "fallback_path_taken_to", label: "Fallback (to)" },
        { key: "selected_scene_function_from", label: "Scene fn (from)" },
        { key: "selected_scene_function_to", label: "Scene fn (to)" },
      ];
      var tableHtml =
        '<div style="overflow-x:auto"><table class="inspector-data-table"><caption class="visually-hidden">Turn comparisons</caption><thead><tr>' +
        cols
          .map(function (c) {
            return "<th>" + escapeHtml(c.label) + "</th>";
          })
          .join("") +
        "</tr></thead><tbody>";
      tableHtml += comparisons
        .map(function (row) {
          return (
            "<tr>" +
            cols
              .map(function (c) {
                var v = row[c.key];
                return "<td>" + escapeHtml(formatDisplayValue(v)) + "</td>";
              })
              .join("") +
            "</tr>"
          );
        })
        .join("");
      tableHtml += "</tbody></table></div>";
      parts.push(tableHtml);
      comparisons.forEach(function (row) {
        parts.push(renderComparisonRowBlocks(row));
      });
    } else {
      parts.push(
        '<p class="manage-empty">No turn-to-turn comparison rows (need at least two turns in session evidence).</p>'
      );
    }
    host.innerHTML = parts.join("");
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

  function initMermaidModeToggle() {
    var sel = byId("inspector-mermaid-mode");
    if (!sel) return;
    sel.addEventListener("change", function () {
      if (!lastTurnPayload) return;
      renderMermaidPanel(lastTurnPayload.decision_trace_projection || {});
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
        var turn = payloads[0] || {};
        var timeline = payloads[1] || {};
        var comparison = payloads[2] || {};
        var coverage = payloads[3] || {};
        var provenance = payloads[4] || {};
        renderTurnPayload(turn);
        renderTimelineViewFixed(timeline);
        renderComparisonViewFixed(comparison);
        renderCoverageView(coverage);
        renderProvenanceView(provenance);
        setText("inspector-timeline-full-json", toPretty(timeline));
        setText("inspector-comparison-full-json", toPretty(comparison));
        setText("inspector-coverage-full-json", toPretty(coverage));
        setText("inspector-provenance-full-json", toPretty(provenance));
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
    initMermaidModeToggle();
    var loadBtn = byId("inspector-load-all");
    if (loadBtn) {
      loadBtn.addEventListener("click", loadWorkbench);
    }
    window.ManageAuth.ensureAuth().catch(function () {});
  });
})();
