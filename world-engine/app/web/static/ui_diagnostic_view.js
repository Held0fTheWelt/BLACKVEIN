/**
 * Structured diagnostic rendering for World-Engine UI (administration-tool WECC / diagnosis parity).
 */
(function () {
  "use strict";

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function stripMarkdownBold(text) {
    return String(text || "").replace(/\*\*/g, "");
  }

  function setHtml(id, html) {
    var el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function renderJsonPre(id, payload, label) {
    var pre = document.getElementById(id);
    if (!pre) return;
    var api = window.WorldEngineUI;
    if (api && typeof api.jsonViewer === "function") {
      api.jsonViewer(pre, payload, { label: label || pre.dataset.jsonLabel || "JSON" });
      return;
    }
    pre.textContent = JSON.stringify(payload || {}, null, 2);
  }

  function pillHtml(label, value, tone) {
    return (
      '<span class="ui-pill ui-pill--' +
      escapeHtml(tone || "neutral") +
      '"><span class="ui-pill-label">' +
      escapeHtml(label) +
      '</span><span class="ui-pill-value">' +
      escapeHtml(value) +
      "</span></span>"
    );
  }

  function statusTone(state) {
    if (state === "healthy" || state === "ready" || state === "ok" || state === "running") return "ok";
    if (state === "blocked" || state === "fail") return "fail";
    if (state === "degraded" || state === "initialized" || state === "warn") return "warn";
    return "neutral";
  }

  function renderPills(containerId, pills) {
    var el = document.getElementById(containerId);
    if (!el) return;
    if (!pills.length) {
      el.innerHTML = "";
      return;
    }
    el.innerHTML = pills.map(function (p) {
      return pillHtml(p.label, p.value, p.tone);
    }).join("");
  }

  function renderKvGrid(containerId, rows) {
    var el = document.getElementById(containerId);
    if (!el) return;
    if (!rows.length) {
      el.innerHTML = '<p class="ui-dx-empty">No fields.</p>';
      return;
    }
    var html = '<dl class="ui-dx-kv-grid">';
    rows.forEach(function (row) {
      html += "<dt>" + escapeHtml(row.label) + "</dt><dd>" + escapeHtml(row.value) + "</dd>";
    });
    html += "</dl>";
    el.innerHTML = html;
  }

  function fillList(ulId, lines) {
    var ul = document.getElementById(ulId);
    if (!ul) return;
    ul.innerHTML = "";
    (lines || []).forEach(function (line) {
      var li = document.createElement("li");
      li.textContent = line;
      ul.appendChild(li);
    });
  }

  function appendIssueItem(ul, item) {
    var li = document.createElement("li");
    li.className = "ui-dx-issue-item";
    var msg = document.createElement("div");
    msg.className = "ui-dx-issue-msg";
    msg.textContent = item.msg;
    li.appendChild(msg);
    if (item.next) {
      var next = document.createElement("div");
      next.className = "ui-dx-issue-next";
      next.textContent = item.next;
      li.appendChild(next);
    }
    ul.appendChild(li);
  }

  function issuePresentation(row) {
    var code = row.code || "";
    var msg = (row.message || code || "").trim();
    if (code) msg = "[" + code + "] " + msg;
    var next = "";
    if (row.suggested_action) {
      next = "Suggested next step: " + stripMarkdownBold(row.suggested_action);
    }
    return { msg: msg, next: next };
  }

  function connectivityGlanceLines(conn) {
    var lines = [];
    if (!conn) return lines;
    if (conn.error && conn.error.message) {
      lines.push("Backend error: " + conn.error.message);
    }
    var ready = conn.backend_to_play_service_ready;
    if (ready && typeof ready === "object") {
      if (ready.status) lines.push("Ready probe status: " + ready.status);
      else if (ready.readiness) lines.push("Readiness: " + ready.readiness);
      else lines.push("Ready probe returned a payload.");
    } else if (!conn.error) {
      lines.push("No ready-probe payload yet.");
    }
    return lines;
  }

  function renderControlCenter(payload) {
    var st = payload.status || {};
    var state = st.state || (st.control_plane_ok ? "healthy" : "blocked");
    var blockerCount = st.blocker_count != null ? st.blocker_count : (payload.blockers || []).length;
    var warningCount = st.warning_count != null ? st.warning_count : (payload.warnings || []).length;
    var summary = payload.operator_summary || {};
    var active = payload.active_runtime || {};

    renderPills("ui-dash-pills", [
      { label: "State", value: state, tone: statusTone(state) },
      { label: "Blockers", value: String(blockerCount), tone: blockerCount > 0 ? "fail" : "ok" },
      { label: "Warnings", value: String(warningCount), tone: warningCount > 0 ? "warn" : "ok" },
      { label: "Runs", value: String(active.run_count != null ? active.run_count : (active.runs && active.runs.items ? active.runs.items.length : 0)), tone: "neutral" },
      {
        label: "Sessions",
        value: String(active.session_count != null ? active.session_count : (active.sessions && active.sessions.items ? active.sessions.items.length : 0)),
        tone: "neutral",
      },
    ]);

    setText(
      "ui-dash-headline",
      summary.headline ||
        (st.control_plane_ok
          ? "Control plane reports no blocking issues."
          : "Review blockers and connectivity before deep session inspection.")
    );
    fillList("ui-dash-sub-lines", summary.sub_lines || []);
    setText("ui-dash-deep-dive", stripMarkdownBold(summary.deep_dive_hint || ""));

    var glance = payload.posture_at_a_glance || {};
    fillList("ui-dash-desired-glance", glance.desired_lines || []);
    fillList("ui-dash-observed-glance", glance.observed_lines || []);
    fillList("ui-dash-connectivity-glance", connectivityGlanceLines(payload.connectivity || {}));

    var blockersUl = document.getElementById("ui-dash-blockers");
    var warningsUl = document.getElementById("ui-dash-warnings");
    if (blockersUl) {
      blockersUl.innerHTML = "";
      var blockers = payload.blockers || [];
      if (!blockers.length) {
        appendIssueItem(blockersUl, { msg: "No blocking issues in this snapshot.", next: "" });
      } else {
        blockers.forEach(function (b) {
          appendIssueItem(blockersUl, issuePresentation(b));
        });
      }
    }
    if (warningsUl) {
      warningsUl.innerHTML = "";
      var warnings = payload.warnings || [];
      if (!warnings.length) {
        appendIssueItem(warningsUl, { msg: "No warnings in this snapshot.", next: "" });
      } else {
        warnings.forEach(function (w) {
          appendIssueItem(warningsUl, issuePresentation(w));
        });
      }
    }

    renderRuntimeTables(active);
    renderJsonPre("ui-dash-audit-desired", payload.desired_play_service_state || {}, "Desired posture");
    renderJsonPre("ui-dash-audit-observed", payload.observed_play_service_state || {}, "Observed posture");
    renderJsonPre("ui-dash-audit-connectivity", payload.connectivity || {}, "Connectivity");
    renderJsonPre("ui-dash-audit-runtime", active, "Active runtime");
    renderJsonPre("ui-dash-audit-snapshot", payload, "Control center snapshot");
  }

  function tableFromItems(items, columns) {
    if (!items.length) {
      return '<p class="ui-dx-empty">None listed.</p>';
    }
    var html = '<div class="ui-dx-table-wrap"><table class="ui-dx-table"><thead><tr>';
    columns.forEach(function (col) {
      html += "<th>" + escapeHtml(col.label) + "</th>";
    });
    html += "</tr></thead><tbody>";
    items.forEach(function (row) {
      html += "<tr>";
      columns.forEach(function (col) {
        var val = col.pick(row);
        html += "<td>" + escapeHtml(val == null ? "—" : val) + "</td>";
      });
      html += "</tr>";
    });
    html += "</tbody></table></div>";
    return html;
  }

  function renderRuntimeTables(active) {
    var runs = (active.runs && active.runs.items) || [];
    var sessions = (active.sessions && active.sessions.items) || [];
    setHtml(
      "ui-dash-runs-table",
      tableFromItems(runs.slice(0, 12), [
        { label: "Run ID", pick: function (r) { return r.id || r.run_id; } },
        { label: "Status", pick: function (r) { return r.status; } },
        { label: "Template", pick: function (r) { return r.template_id || r.template_title; } },
      ])
    );
    setHtml(
      "ui-dash-sessions-table",
      tableFromItems(sessions.slice(0, 12), [
        { label: "Session", pick: function (s) { return s.session_id || s.id; } },
        { label: "Module", pick: function (s) { return s.module_id; } },
        { label: "Turn", pick: function (s) { return s.turn_counter != null ? String(s.turn_counter) : ""; } },
        { label: "Scene", pick: function (s) { return s.current_scene_id; } },
      ])
    );
    if (active.runs_error && active.runs_error.message) {
      setHtml("ui-dash-runs-table", '<p class="ui-dx-empty ui-dx-empty--error">' + escapeHtml(active.runs_error.message) + "</p>");
    }
    if (active.sessions_error && active.sessions_error.message) {
      setHtml("ui-dash-sessions-table", '<p class="ui-dx-empty ui-dx-empty--error">' + escapeHtml(active.sessions_error.message) + "</p>");
    }
  }

  function renderReadinessAuthority(payload) {
    if (!payload || typeof payload !== "object") {
      setHtml("ui-dash-readiness-summary", '<p class="ui-dx-empty">No readiness payload.</p>');
      return;
    }
    var ready = !!payload.runtime_session_ready;
    var canExec = !!payload.can_execute;
    renderPills("ui-dash-readiness-pills", [
      { label: "runtime_session_ready", value: ready ? "true" : "false", tone: ready ? "ok" : "fail" },
      { label: "can_execute", value: canExec ? "true" : "false", tone: canExec ? "ok" : "warn" },
    ]);
    var rows = [
      { label: "Session ID", value: payload.session_id || "(none — inventory mode)" },
      { label: "ready_for_play", value: String(!!payload.ready_for_play) },
    ];
    var chain = payload.source_of_truth_chain;
    if (Array.isArray(chain) && chain.length) {
      rows.push({
        label: "Source chain",
        value: chain.map(function (c) { return (c.source || "?") + ":" + (c.status || "?"); }).join(" · "),
      });
    }
    var signals = payload.degradation_signals;
    if (Array.isArray(signals) && signals.length) {
      rows.push({ label: "Degradation signals", value: String(signals.length) + " signal(s)" });
    }
    renderKvGrid("ui-dash-readiness-summary", rows);

    var warnUl = document.getElementById("ui-dash-readiness-warnings");
    if (warnUl) {
      warnUl.innerHTML = "";
      var warnings = payload.warnings || [];
      if (!warnings.length) {
        appendIssueItem(warnUl, { msg: "No readiness warnings.", next: "" });
      } else {
        warnings.forEach(function (w) {
          appendIssueItem(warnUl, { msg: typeof w === "string" ? w : JSON.stringify(w), next: "" });
        });
      }
    }
    renderJsonPre("ui-dash-audit-readiness", payload, "Runtime readiness authority");
  }

  window.WorldEngineDiagnosticView = {
    escapeHtml: escapeHtml,
    renderControlCenter: renderControlCenter,
    renderReadinessAuthority: renderReadinessAuthority,
    renderJsonPre: renderJsonPre,
  };
})();
