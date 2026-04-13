(function () {
  var state = {
    presets: null,
    advanced: null,
    effective: null,
    changes: null
  };

  function show(kind, msg) {
    var err = document.getElementById("manage-rs-banner");
    var ok = document.getElementById("manage-rs-success");
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
      return;
    }
    if (err) {
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

  function fillLines(id, lines, fallback) {
    var node = document.getElementById(id);
    if (!node) return;
    node.innerHTML = "";
    (lines || []).forEach(function (line) {
      var li = document.createElement("li");
      li.textContent = line;
      node.appendChild(li);
    });
    if (!lines || !lines.length) {
      var empty = document.createElement("li");
      empty.textContent = fallback || "No entries.";
      node.appendChild(empty);
    }
  }

  function setValue(id, val) {
    var node = document.getElementById(id);
    if (node) node.value = val == null ? "" : String(val);
  }

  function setChecked(id, val) {
    var node = document.getElementById(id);
    if (node) node.checked = !!val;
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

  function setJson(payload) {
    var node = document.getElementById("manage-rs-json");
    if (!node) return;
    node.textContent = JSON.stringify(payload || {}, null, 2);
  }

  function renderPresets() {
    var holder = document.getElementById("manage-rs-presets");
    if (!holder) return;
    holder.innerHTML = "";
    var payload = state.presets || {};
    (payload.presets || []).forEach(function (preset) {
      var box = document.createElement("section");
      box.className = "panel";
      box.style.marginBottom = "0.75rem";

      var title = document.createElement("h3");
      title.textContent = preset.display_name + " (" + preset.preset_id + ")";
      box.appendChild(title);

      var meta = document.createElement("p");
      meta.className = "muted";
      meta.textContent = "Stability: " + (preset.stability || "unknown")
        + " | Local-only: " + (preset.is_local_only ? "yes" : "no")
        + (preset.is_active ? " | ACTIVE" : "");
      box.appendChild(meta);

      var desc = document.createElement("p");
      desc.className = "muted";
      desc.textContent = preset.description || "";
      box.appendChild(desc);

      var impact = document.createElement("ul");
      impact.className = "muted";
      (preset.impact_summary || []).forEach(function (line) {
        var li = document.createElement("li");
        li.textContent = line;
        impact.appendChild(li);
      });
      box.appendChild(impact);

      var actions = document.createElement("div");
      actions.className = "manage-actions-row";
      var applyBtn = document.createElement("button");
      applyBtn.type = "button";
      applyBtn.className = "btn";
      applyBtn.textContent = preset.is_active ? "Active preset" : "Apply preset";
      applyBtn.disabled = !!preset.is_active;
      applyBtn.setAttribute("data-preset-id", preset.preset_id);
      applyBtn.addEventListener("click", function () {
        applyPreset(preset.preset_id, false);
      });
      actions.appendChild(applyBtn);
      box.appendChild(actions);
      holder.appendChild(box);
    });
  }

  function renderAdvancedSettings() {
    var settings = ((state.advanced || {}).settings) || {};
    setValue("manage-rs-generation-mode", settings.generation_execution_mode || "mock_only");
    setValue("manage-rs-validation-mode", settings.validation_execution_mode || "schema_only");
    setValue("manage-rs-provider-mode", settings.provider_selection_mode || "local_only");
    setValue("manage-rs-runtime-profile", settings.runtime_profile || "safe_local");
    setValue("manage-rs-retrieval-mode", settings.retrieval_execution_mode || "disabled");
    setValue("manage-rs-retrieval-profile", settings.retrieval_profile || "runtime_turn_support");
    setValue("manage-rs-retrieval-topk", settings.retrieval_top_k == null ? 4 : settings.retrieval_top_k);
    setValue("manage-rs-retrieval-min-score", settings.retrieval_min_score == null ? "" : settings.retrieval_min_score);
    setChecked("manage-rs-embeddings", settings.embeddings_enabled);
    setChecked("manage-rs-corrective", settings.enable_corrective_feedback);
    setValue("manage-rs-verbosity", settings.runtime_diagnostics_verbosity || "operator");
    setValue("manage-rs-max-retry", settings.max_retry_attempts == null ? 1 : settings.max_retry_attempts);
  }

  function renderEffective() {
    var payload = state.effective || {};
    fillLines("manage-rs-effective-summary", [
      "Active preset: " + (payload.active_preset_id || "safe_local"),
      "Override count: " + (payload.override_count || 0),
      "Drift keys: " + ((payload.drift_keys || []).length || 0),
      "Requires refresh: " + (payload.requires_refresh ? "yes" : "no")
    ], "No effective config data.");

    fillLines("manage-rs-guardrail-lines", (payload.guardrail_warnings || []).map(function (row) {
      return "[" + (row.severity || "info") + "] " + (row.message || "");
    }), "No guardrail warnings.");

    var sourceLines = (payload.value_sources || []).slice(0, 14).map(function (row) {
      return row.key + ": source=" + row.source + " | effective=" + JSON.stringify(row.derived_effective_value);
    });
    fillLines("manage-rs-source-lines", sourceLines, "No source metadata.");
  }

  function renderChanges() {
    var items = ((state.changes || {}).items) || [];
    fillLines("manage-rs-change-lines", items.map(function (row) {
      return (row.changed_at || "?") + " | " + (row.changed_by || "system") + " | "
        + (row.scope || "scope") + " | " + (row.summary || row.event_type || "change");
    }), "No recent settings changes.");
  }

  function renderAll() {
    renderPresets();
    renderAdvancedSettings();
    renderEffective();
    renderChanges();
    setJson({
      presets: state.presets,
      advanced: state.advanced,
      effective: state.effective,
      changes: state.changes
    });
  }

  function loadPresets() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/presets").then(function (res) {
      state.presets = res && res.data ? res.data : {};
    });
  }

  function loadAdvanced() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/advanced-settings").then(function (res) {
      state.advanced = res && res.data ? res.data : {};
    });
  }

  function loadEffective() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/effective-config").then(function (res) {
      state.effective = res && res.data ? res.data : {};
    });
  }

  function loadChanges() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/settings-changes?limit=25").then(function (res) {
      state.changes = res && res.data ? res.data : {};
    });
  }

  function refreshAll() {
    return Promise.all([loadPresets(), loadAdvanced(), loadEffective(), loadChanges()]).then(function () {
      renderAll();
    });
  }

  function collectAdvancedPayload() {
    var payload = {
      generation_execution_mode: value("manage-rs-generation-mode", "mock_only"),
      validation_execution_mode: value("manage-rs-validation-mode", "schema_only"),
      provider_selection_mode: value("manage-rs-provider-mode", "local_only"),
      runtime_profile: value("manage-rs-runtime-profile", "safe_local"),
      retrieval_execution_mode: value("manage-rs-retrieval-mode", "disabled"),
      retrieval_profile: value("manage-rs-retrieval-profile", "runtime_turn_support"),
      retrieval_top_k: parseInt(value("manage-rs-retrieval-topk", "4"), 10) || 4,
      embeddings_enabled: checked("manage-rs-embeddings"),
      enable_corrective_feedback: checked("manage-rs-corrective"),
      runtime_diagnostics_verbosity: value("manage-rs-verbosity", "operator"),
      max_retry_attempts: parseInt(value("manage-rs-max-retry", "1"), 10) || 0
    };
    var minScoreRaw = value("manage-rs-retrieval-min-score", "");
    payload.retrieval_min_score = minScoreRaw === "" ? null : parseFloat(minScoreRaw);
    return payload;
  }

  function applyPreset(presetId, keepOverrides) {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/presets/apply", {
      method: "POST",
      body: JSON.stringify({
        preset_id: presetId,
        keep_overrides: !!keepOverrides
      })
    }).then(function () {
      return refreshAll().then(function () {
        show("ok", "Preset applied: " + presetId);
      });
    }).catch(function (err) {
      show("err", parseError(err));
    });
  }

  function resetOverrides() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/advanced-settings/reset-overrides", {
      method: "POST",
      body: "{}"
    }).then(function () {
      return refreshAll().then(function () {
        show("ok", "Overrides cleared and preset reapplied.");
      });
    }).catch(function (err) {
      show("err", parseError(err));
    });
  }

  function saveAdvancedSettings() {
    var payload = collectAdvancedPayload();
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/advanced-settings", {
      method: "PATCH",
      body: JSON.stringify(payload)
    }).then(function () {
      return refreshAll().then(function () {
        show("ok", "Advanced settings saved.");
      });
    }).catch(function (err) {
      show("err", parseError(err));
    });
  }

  function bindActions() {
    var refresh = document.getElementById("manage-rs-refresh");
    if (refresh) {
      refresh.addEventListener("click", function () {
        show(null, "");
        refreshAll().catch(function (err) {
          show("err", parseError(err));
        });
      });
    }
    var save = document.getElementById("manage-rs-save-settings");
    if (save) {
      save.addEventListener("click", function () {
        saveAdvancedSettings();
      });
    }
    var reset = document.getElementById("manage-rs-reset-overrides");
    if (reset) {
      reset.addEventListener("click", function () {
        resetOverrides();
      });
    }
    var safe = document.getElementById("manage-rs-apply-safe-local");
    if (safe) {
      safe.addEventListener("click", function () {
        applyPreset("safe_local", false);
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.ManageAuth) return;
    window.ManageAuth.ensureAuth().then(function () {
      bindActions();
      return refreshAll();
    }).catch(function (err) {
      show("err", parseError(err));
    });
  });
})();
