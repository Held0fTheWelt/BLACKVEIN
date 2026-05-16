(function () {
  function show(kind, msg) {
    var err = document.getElementById("manage-rd-banner");
    var ok = document.getElementById("manage-rd-success");
    if (err) {
      err.style.display = "none";
      err.textContent = "";
    }
    if (ok) {
      ok.style.display = "none";
      ok.textContent = "";
    }
    if (!msg) return;
    if (kind === "ok" && ok) {
      ok.style.display = "";
      ok.textContent = msg;
    } else if (err) {
      err.style.display = "";
      err.textContent = msg;
    }
  }

  function parseError(err) {
    if (!err) return "Request failed";
    if (typeof err.message === "string" && err.message) return err.message;
    if (err.body && window.ManageAuth && typeof window.ManageAuth.formatApiErrorMessage === "function") {
      return window.ManageAuth.formatApiErrorMessage(err.body, err.status);
    }
    return "Request failed";
  }

  function appendOperatorRow(ul, row, ordered) {
    var li = document.createElement("li");
    li.className = ordered ? "" : "manage-og-blocker-item";
    if (typeof row === "string") {
      li.textContent = row;
    } else if (row && typeof row === "object") {
      var msg = document.createElement("div");
      msg.className = ordered ? "" : "manage-og-blocker-msg";
      var domain = row.domain || "domain";
      var text = row.message || "";
      if (row.code && text.indexOf("[") !== 0) {
        text = "[" + row.code + "] " + text;
      }
      msg.textContent = domain + ": " + text;
      li.appendChild(msg);
      if (row.suggested_action) {
        var next = document.createElement("div");
        next.className = "manage-og-blocker-next";
        next.textContent = (ordered ? "Next: " : "Suggested next step: ") + row.suggested_action;
        li.appendChild(next);
      }
    } else {
      li.textContent = String(row);
    }
    ul.appendChild(li);
  }

  function fillList(id, lines, ordered) {
    var node = document.getElementById(id);
    if (!node) return;
    node.innerHTML = "";
    (lines || []).forEach(function (line) {
      appendOperatorRow(node, line, ordered);
    });
    if (!lines || !lines.length) {
      var empty = document.createElement("li");
      empty.textContent = ordered ? "No actions listed." : "No active blockers.";
      node.appendChild(empty);
    }
  }

  function updateBlockersRailBadge(blockerCount, warningCount) {
    var rail = document.querySelector('.mui-rail-btn[data-deck-target="blockers"] .mui-rail-badge');
    if (!rail) return;
    rail.className = "mui-rail-badge";
    if (blockerCount > 0) {
      rail.classList.add("mui-rail-badge--fail");
    } else if (warningCount > 0) {
      rail.classList.add("mui-rail-badge--warn");
    } else {
      rail.classList.add("mui-rail-badge--ok");
    }
  }

  function setJson(id, payload) {
    var node = document.getElementById(id);
    if (!node) return;
    node.textContent = JSON.stringify(payload || {}, null, 2);
  }

  function renderSummary(summary) {
    var lines = [];
    var providers = summary.provider_readiness || {};
    var routes = summary.model_route_readiness || {};
    var rag = summary.rag || {};
    var orchestration = summary.orchestration || {};
    var world = summary.world_engine || {};
    var active = summary.active_runtime || {};
    var settingsLayer = summary.settings_layer || {};
    lines.push("AI-only valid: " + (summary.ai_only_valid ? "yes" : "no"));
    if (summary.task_routes_green != null) {
      lines.push("Task routes (operator green): " + (summary.task_routes_green ? "yes" : "no"));
    }
    lines.push("Providers: " + (providers.total || 0) + " total, " + (providers.eligible_non_mock || 0) + " eligible non-mock");
    lines.push("Routes: " + (routes.total || 0) + " total, " + (routes.ai_ready || 0) + " AI-ready");
    lines.push("RAG: " + (rag.chunk_count || 0) + " chunks, embedding backend " + (rag.embedding_backend_available ? "available" : "unavailable"));
    lines.push("Orchestration: LangGraph " + (orchestration.langgraph_dependency_available ? "available" : "unavailable") + ", LangChain " + (orchestration.langchain_bridge_available ? "available" : "unavailable"));
    lines.push("World-engine control plane ok: " + (world.control_plane_ok ? "yes" : "no") + " | runs " + (active.run_count || 0) + " | sessions " + (active.session_count || 0));
    lines.push("Runtime settings layer: preset " + (settingsLayer.active_preset_id || "safe_local") + ", overrides " + (settingsLayer.override_count || 0) + ", warnings " + (settingsLayer.guardrail_warning_count || 0));
    fillList("manage-rd-summary-lines", lines, false);
  }

  function renderDomainStatus(rows) {
    fillList("manage-rd-domain-status", (rows || []).map(function (row) {
      return "[" + (row.state || "unknown") + "] " + (row.domain || "domain")
        + " -> " + (row.consequence || "")
        + (row.fix_path ? " (fix: " + row.fix_path + ")" : "");
    }), false);
  }

  function renderLinks(links) {
    var node = document.getElementById("manage-rd-links");
    if (!node) return;
    node.innerHTML = "";
    (links || []).forEach(function (row) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = row.path || "#";
      a.textContent = row.label || row.path || "Open";
      li.appendChild(a);
      node.appendChild(li);
    });
  }

  function loadDashboard() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/runtime-dashboard").then(function (res) {
      var payload = res && res.data ? res.data : {};
      renderSummary(payload.summary || {});
      fillList("manage-rd-blockers", payload.blockers || [], false);
      fillList("manage-rd-next-actions", payload.next_actions || [], true);
      renderDomainStatus(payload.domain_status || []);
      fillList("manage-rd-degraded", payload.degraded_or_warning || [], false);
      renderLinks(payload.links || []);
      updateBlockersRailBadge((payload.blockers || []).length, (payload.degraded_or_warning || []).length);
      setJson("manage-rd-json", payload);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.ManageAuth) return;
    window.ManageAuth.ensureAuth().then(function () {
      return loadDashboard();
    }).catch(function (err) {
      show("err", parseError(err));
    });
    var refresh = document.getElementById("manage-rd-refresh");
    if (refresh) {
      refresh.addEventListener("click", function () {
        show(null, "");
        loadDashboard().catch(function (err) {
          show("err", parseError(err));
        });
      });
    }
  });
})();
