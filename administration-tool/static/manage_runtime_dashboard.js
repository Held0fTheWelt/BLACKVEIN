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

  function fillList(id, lines, ordered) {
    var node = document.getElementById(id);
    if (!node) return;
    node.innerHTML = "";
    (lines || []).forEach(function (line) {
      var li = document.createElement("li");
      if (typeof line === "string") {
        li.textContent = line;
      } else if (line && typeof line === "object") {
        li.textContent = (line.domain || "domain") + ": " + (line.message || "");
      } else {
        li.textContent = String(line);
      }
      node.appendChild(li);
    });
    if (!lines || !lines.length) {
      var empty = document.createElement("li");
      empty.textContent = ordered ? "No actions listed." : "No active blockers.";
      node.appendChild(empty);
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
    lines.push("Providers: " + (providers.total || 0) + " total, " + (providers.eligible_non_mock || 0) + " eligible non-mock");
    lines.push("Routes: " + (routes.total || 0) + " total, " + (routes.ai_ready || 0) + " AI-ready");
    lines.push("RAG: " + (rag.chunk_count || 0) + " chunks, embedding backend " + (rag.embedding_backend_available ? "available" : "unavailable"));
    lines.push("Orchestration: LangGraph " + (orchestration.langgraph_dependency_available ? "available" : "unavailable") + ", LangChain " + (orchestration.langchain_bridge_available ? "available" : "unavailable"));
    lines.push("World-engine control plane ok: " + (world.control_plane_ok ? "yes" : "no") + " | runs " + (active.run_count || 0) + " | sessions " + (active.session_count || 0));
    lines.push("Runtime settings layer: preset " + (settingsLayer.active_preset_id || "safe_local") + ", overrides " + (settingsLayer.override_count || 0) + ", warnings " + (settingsLayer.guardrail_warning_count || 0));
    fillList("manage-rd-summary-lines", lines, false);
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
      renderLinks(payload.links || []);
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
