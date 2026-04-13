(function () {
  var state = { status: null, settings: null };

  function show(kind, msg) {
    var err = document.getElementById("manage-orch-banner");
    var ok = document.getElementById("manage-orch-success");
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

  function setJson(id, payload) {
    var box = document.getElementById(id);
    if (!box) return;
    box.textContent = JSON.stringify(payload || {}, null, 2);
  }

  function fillLines(id, lines, fallback) {
    var ul = document.getElementById(id);
    if (!ul) return;
    ul.innerHTML = "";
    (lines || []).forEach(function (line) {
      var li = document.createElement("li");
      li.textContent = line;
      ul.appendChild(li);
    });
    if (!lines || !lines.length) {
      var li = document.createElement("li");
      li.textContent = fallback || "None";
      ul.appendChild(li);
    }
  }

  function value(id, fallback) {
    var node = document.getElementById(id);
    if (!node) return fallback || "";
    return (node.value || fallback || "").trim();
  }

  function checked(id) {
    var node = document.getElementById(id);
    return !!(node && node.checked);
  }

  function setValue(id, val) {
    var node = document.getElementById(id);
    if (node) node.value = val == null ? "" : String(val);
  }

  function setChecked(id, val) {
    var node = document.getElementById(id);
    if (node) node.checked = !!val;
  }

  function renderStatus(payload) {
    state.status = payload || {};
    var lg = state.status.langgraph || {};
    var lc = state.status.langchain || {};
    fillLines("manage-orch-langgraph-lines", [
      "Dependency available: " + (lg.dependency_available ? "yes" : "no"),
      "Runtime profile: " + (lg.runtime_profile || "?") + " | validation mode: " + (lg.validation_execution_mode || "?"),
      "Corrective feedback: " + (lg.enable_corrective_feedback ? "enabled" : "disabled"),
      "Diagnostics verbosity: " + (lg.runtime_diagnostics_verbosity || "operator"),
      "Max retry attempts: " + (lg.max_retry_attempts == null ? "?" : lg.max_retry_attempts),
      "Fallback markers (recent): " + ((lg.fallback_posture || {}).fallback_marker_count_recent || 0),
      "Graph errors (recent): " + ((lg.fallback_posture || {}).graph_error_count_recent || 0)
    ], "No LangGraph status.");
    var execSummary = lg.recent_execution_summary || {};
    fillLines("manage-orch-exec-lines", [
      "Sessions sampled: " + (execSummary.sessions_sampled || 0),
      "Top nodes: " + ((execSummary.top_nodes_executed || []).map(function (row) { return row[0] + ":" + row[1]; }).join(", ") || "none"),
      "Diagnostics errors: " + ((execSummary.diagnostics_errors || []).length || 0)
    ], "No execution summary.");
    fillLines("manage-orch-langchain-lines", [
      "Bridge available: " + (lc.bridge_available ? "yes" : "no"),
      "Runtime adapter bridge: " + (lc.runtime_adapter_bridge_available ? "available" : "unavailable"),
      "Retriever bridge: " + (lc.retriever_bridge_available ? "available" : "unavailable"),
      "Writers-room bridge: " + (lc.writers_room_bridge_available ? "available" : "unavailable"),
      "Tool bridge: " + (lc.tool_bridge_available ? "available" : "unavailable"),
      "Runtime parser health: " + ((lc.parser_schema_health || {}).runtime_structured_output ? "ok" : "fail"),
      "Writers-room parser health: " + ((lc.parser_schema_health || {}).writers_room_structured_output ? "ok" : "fail"),
      "Recent parser failure count: " + (lc.recent_parser_failure_count || 0)
    ], "No LangChain status.");
    setJson("manage-orch-json", { status: state.status, settings: state.settings });
  }

  function renderSettings(payload) {
    state.settings = payload || {};
    setValue("manage-orch-setting-runtime-profile", state.settings.runtime_profile || "safe_local");
    setValue("manage-orch-setting-verbosity", state.settings.runtime_diagnostics_verbosity || "operator");
    setValue("manage-orch-setting-max-retry", state.settings.max_retry_attempts == null ? 1 : state.settings.max_retry_attempts);
    setChecked("manage-orch-setting-corrective", state.settings.enable_corrective_feedback);
    setJson("manage-orch-json", { status: state.status, settings: state.settings });
  }

  function loadStatus() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/orchestration/status").then(function (res) {
      renderStatus(res && res.data ? res.data : {});
    });
  }

  function loadSettings() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/orchestration/settings").then(function (res) {
      renderSettings(res && res.data ? res.data : {});
    });
  }

  function refreshAll() {
    return Promise.all([loadStatus(), loadSettings()]);
  }

  function bindActions() {
    var save = document.getElementById("manage-orch-save-settings");
    if (!save) return;
    save.addEventListener("click", function () {
      var body = {
        runtime_profile: value("manage-orch-setting-runtime-profile", "safe_local"),
        runtime_diagnostics_verbosity: value("manage-orch-setting-verbosity", "operator"),
        max_retry_attempts: parseInt(value("manage-orch-setting-max-retry", "1"), 10) || 0,
        enable_corrective_feedback: checked("manage-orch-setting-corrective")
      };
      window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/orchestration/settings", {
        method: "PATCH",
        body: JSON.stringify(body)
      }).then(function () {
        return refreshAll().then(function () {
          show("ok", "Orchestration settings saved.");
        });
      }).catch(function (err) {
        show("err", parseError(err));
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.ManageAuth) return;
    window.ManageAuth.ensureAuth().then(function () {
      bindActions();
      return refreshAll();
    }).catch(function (err) {
      show("err", parseError(err));
    });
    var refresh = document.getElementById("manage-orch-refresh");
    if (refresh) {
      refresh.addEventListener("click", function () {
        show(null, "");
        refreshAll().catch(function (err) {
          show("err", parseError(err));
        });
      });
    }
  });
})();
