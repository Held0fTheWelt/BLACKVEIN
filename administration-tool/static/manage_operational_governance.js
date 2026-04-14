/**
 * AI Runtime Governance admin surface.
 */
(function () {
  var state = {
    providers: [],
    models: [],
    routes: [],
  };

  /** Unwrap governance envelope `{ ok, data }` when present. */
  function govPayload(res) {
    if (res && res.data !== undefined && Object.prototype.hasOwnProperty.call(res, "ok")) {
      return res.data || {};
    }
    return res || {};
  }

  function show(kind, msg) {
    var errEl = document.getElementById("manage-og-banner");
    var okEl = document.getElementById("manage-og-success");
    if (errEl) {
      errEl.style.display = "none";
      errEl.textContent = "";
    }
    if (okEl) {
      okEl.style.display = "none";
      okEl.textContent = "";
    }
    if (!msg) return;
    if (kind === "ok" && okEl) {
      okEl.style.display = "";
      okEl.textContent = msg;
    } else if (errEl) {
      errEl.style.display = "";
      errEl.textContent = msg;
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

  function setSelectOptions(id, values, valueKey, labelBuilder, includeEmpty) {
    var select = document.getElementById(id);
    if (!select) return;
    var current = select.value;
    select.innerHTML = "";
    if (includeEmpty) {
      var emptyOption = document.createElement("option");
      emptyOption.value = "";
      emptyOption.textContent = "Select…";
      select.appendChild(emptyOption);
    }
    (values || []).forEach(function (item) {
      var option = document.createElement("option");
      option.value = item[valueKey];
      option.textContent = labelBuilder(item);
      select.appendChild(option);
    });
    if (current) {
      select.value = current;
    }
  }

  function setJson(id, payload) {
    var box = document.getElementById(id);
    if (!box) return;
    box.textContent = JSON.stringify(payload || {}, null, 2);
  }

  function checked(id) {
    var node = document.getElementById(id);
    return !!(node && node.checked);
  }

  function value(id, fallback) {
    var node = document.getElementById(id);
    if (!node) return fallback || "";
    return (node.value || fallback || "").trim();
  }

  function setValue(id, val) {
    var node = document.getElementById(id);
    if (node) node.value = val == null ? "" : String(val);
  }

  function setChecked(id, val) {
    var node = document.getElementById(id);
    if (node) node.checked = !!val;
  }

  function providerOptionLabel(p) {
    var bits = [];
    bits.push(p.is_enabled ? "ON" : "OFF");
    bits.push((p.display_name && String(p.display_name).trim()) || p.provider_id);
    bits.push("id:" + p.provider_id);
    bits.push(String(p.provider_type || "?"));
    bits.push("health:" + (p.health_status || "?"));
    bits.push(p.eligible_for_runtime_assignment ? "eligible" : "not eligible");
    return bits.join(" · ");
  }

  function modelOptionLabel(m) {
    var bits = [];
    bits.push(m.is_enabled ? "ON" : "OFF");
    bits.push((m.display_name && String(m.display_name).trim()) || m.model_id);
    bits.push("id:" + m.model_id);
    bits.push("provider:" + (m.provider_id || "?"));
    bits.push(m.runtime_eligible ? "runtime-eligible" : "blocked");
    return bits.join(" · ");
  }

  function routeOptionLabel(r) {
    var bits = [];
    bits.push(r.is_enabled ? "ON" : "OFF");
    bits.push("route " + r.route_id);
    bits.push("task " + (r.task_kind || "?"));
    bits.push(r.ai_path_ready ? "AI path OK" : "AI path blocked");
    bits.push(r.runtime_eligible ? "eligible for runtime" : "not eligible");
    return bits.join(" · ");
  }

  function blockerKindLabel(code) {
    var c = (code || "").toLowerCase();
    if (c.indexOf("missing") >= 0 || c.indexOf("_missing") >= 0) return "Missing setup";
    if (c.indexOf("health") >= 0 || c.indexOf("connect") >= 0 || c.indexOf("unavailable") >= 0) return "External / health";
    if (c.lastIndexOf("route_", 0) === 0 || c.indexOf("enabled_ai") >= 0) return "Route configuration";
    if (c.lastIndexOf("provider_", 0) === 0) return "Provider configuration";
    return "Configuration";
  }

  function appendReadinessBlocker(ul, b) {
    var li = document.createElement("li");
    li.className = "manage-og-blocker-item";
    var kind = document.createElement("div");
    kind.className = "manage-og-blocker-kind";
    kind.textContent = blockerKindLabel(b.code);
    var msg = document.createElement("div");
    msg.className = "manage-og-blocker-msg";
    var body = (b.message || b.code || "").trim();
    if (b.entity_type && b.entity_id) body = "(" + b.entity_type + " " + b.entity_id + ") " + body;
    else if (b.entity_type && !b.entity_id) body = "(Global — " + b.entity_type + ") " + body;
    msg.textContent = body;
    li.appendChild(kind);
    li.appendChild(msg);
    if (b.suggested_action) {
      var act = document.createElement("div");
      act.className = "manage-og-blocker-next";
      act.textContent = "Next step: " + String(b.suggested_action).replace(/\*\*/g, "");
      li.appendChild(act);
    }
    ul.appendChild(li);
  }

  function renderReadinessPanel(data) {
    var head = document.getElementById("manage-og-readiness-headline");
    var sev = document.getElementById("manage-og-readiness-severity");
    var sevRow = document.getElementById("manage-og-readiness-severity-row");
    var badge = document.getElementById("manage-og-readiness-badge");
    var inv = document.getElementById("manage-og-readiness-inventory");
    var leg = document.getElementById("manage-og-readiness-legend");
    var ulB = document.getElementById("manage-og-readiness-blockers");
    var olN = document.getElementById("manage-og-readiness-next");
    if (head) {
      head.textContent = data.readiness_headline || (data.ai_only_valid
        ? "AI-only generation is currently valid for governed routes."
        : "mock_only remains the safe default until the blockers below are resolved.");
    }
    if (sev && sevRow && badge) {
      var s = data.readiness_severity || "";
      if (s) {
        sevRow.style.display = "";
        badge.textContent = s === "healthy" ? "Healthy" : s === "blocked" ? "Blocked" : s === "degraded" ? "Degraded" : "Unknown";
        badge.className = "manage-severity-badge manage-severity-badge--" + s;
        var parts = [];
        parts.push("Severity is " + s + ".");
        if (data.mock_only_required) parts.push("The stack still requires mock-only or hybrid fallback until every blocker is cleared.");
        if (data.ai_only_valid) parts.push("Preconditions for AI-only generation are satisfied — change modes only after operational sign-off.");
        sev.textContent = parts.join(" ");
      } else {
        sevRow.style.display = "none";
        sev.textContent = "";
        badge.textContent = "";
        badge.className = "manage-severity-badge";
      }
    }
    if (inv) {
      var ps = data.provider_summary || {};
      var ms = data.model_summary || {};
      var rs = data.route_summary || {};
      inv.textContent = "Inventory snapshot: " + (ps.total || 0) + " providers (" + (ps.eligible_non_mock || 0) + " non-mock eligible), "
        + (ms.total || 0) + " models (" + (ms.runtime_eligible_non_mock || 0) + " non-mock runtime-eligible), "
        + (rs.total || 0) + " routes (" + (rs.ai_ready || 0) + " with AI path ready, " + (rs.runtime_eligible || 0) + " runtime-eligible).";
    }
    if (leg) {
      leg.innerHTML = "";
      var legend = data.readiness_legend || [];
      if (!legend.length) {
        legend = [
          "mock_only_required explains why the stack is not ready for ai_only.",
          "ai_only_valid confirms provider, model, and route preconditions.",
        ];
      }
      legend.forEach(function (line) {
        var li = document.createElement("li");
        li.textContent = line;
        leg.appendChild(li);
      });
    }
    if (ulB) {
      ulB.innerHTML = "";
      var blockers = data.blockers || [];
      var cap = 18;
      for (var i = 0; i < blockers.length && i < cap; i++) {
        appendReadinessBlocker(ulB, blockers[i]);
      }
      if (blockers.length > cap) {
        var more = document.createElement("li");
        more.className = "manage-og-blocker-item";
        more.textContent = "… and " + (blockers.length - cap) + " more — open technical audit JSON below for the full list.";
        ulB.appendChild(more);
      }
      if (!blockers.length) {
        var none = document.createElement("li");
        none.className = "manage-og-blocker-item";
        none.textContent = "No blocking issues reported. Still run provider health checks before switching away from mock_only.";
        ulB.appendChild(none);
      }
    }
    if (olN) {
      olN.innerHTML = "";
      (data.next_actions || []).forEach(function (na) {
        var li = document.createElement("li");
        li.textContent = na;
        olN.appendChild(li);
      });
    }
  }

  function loadProviders() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/providers").then(function (res) {
      var inner = govPayload(res);
      state.providers = inner.providers || [];
      setSelectOptions("manage-og-provider-select", state.providers, "provider_id", providerOptionLabel, true);
      setSelectOptions("manage-og-model-provider", state.providers, "provider_id", providerOptionLabel, false);
      setJson("manage-og-providers-json", { providers: state.providers });
    });
  }

  function loadModels() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/models").then(function (res) {
      var inner = govPayload(res);
      state.models = inner.models || [];
      setSelectOptions("manage-og-model-select", state.models, "model_id", modelOptionLabel, true);
      setSelectOptions("manage-og-route-preferred-model", state.models, "model_id", modelOptionLabel, true);
      setSelectOptions("manage-og-route-fallback-model", state.models, "model_id", modelOptionLabel, true);
      setSelectOptions("manage-og-route-mock-model", state.models, "model_id", modelOptionLabel, true);
      setJson("manage-og-models-json", { models: state.models });
    });
  }

  function loadRoutes() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/routes").then(function (res) {
      var inner = govPayload(res);
      state.routes = inner.routes || [];
      setSelectOptions("manage-og-route-select", state.routes, "route_id", routeOptionLabel, true);
      setJson("manage-og-routes-json", { routes: state.routes });
    });
  }

  function loadModes() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/runtime/modes").then(function (res) {
      var data = govPayload(res);
      setValue("manage-og-generation-mode", data.generation_execution_mode);
      setValue("manage-og-retrieval-mode", data.retrieval_execution_mode);
      setValue("manage-og-validation-mode", data.validation_execution_mode);
      setValue("manage-og-provider-selection", data.provider_selection_mode);
      setValue("manage-og-runtime-profile", data.runtime_profile);
    });
  }

  function loadResolved() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/runtime/resolved-config").then(function (res) {
      setJson("manage-og-runtime-config", govPayload(res) || {});
    });
  }

  function loadReadiness() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/runtime-readiness").then(function (res) {
      var data = govPayload(res);
      renderReadinessPanel(data);
      setJson("manage-og-readiness-json", data || {});
    });
  }

  function renderPanelHints() {
    var hp = document.getElementById("manage-og-hint-providers");
    var hm = document.getElementById("manage-og-hint-models");
    var hr = document.getElementById("manage-og-hint-routes");
    var pc = (state.providers || []).length;
    var mc = (state.models || []).length;
    var rc = (state.routes || []).length;
    if (hp) {
      hp.textContent = pc === 0
        ? "No providers yet. Create a provider, then add credentials for non-mock types before attaching models."
        : pc + " provider(s) loaded. Choose one to inspect health, eligibility, and limitations.";
    }
    if (hm) {
      hm.textContent = mc === 0
        ? "No models yet. Models must reference a provider; create a provider first."
        : mc + " model(s) loaded. Each model belongs to one provider — align roles and timeouts before wiring routes.";
    }
    if (hr) {
      hr.textContent = rc === 0
        ? "No routes yet. Routes bind task kinds to preferred/fallback/mock models."
        : rc + " route(s) loaded. Preferred and fallback models should point at healthy, enabled models for AI paths.";
    }
  }

  function refreshAll(opts) {
    if (!(opts && opts.preserveBanner)) show(null, "");
    return Promise.all([
      loadProviders(),
      loadModels(),
      loadRoutes(),
      loadModes(),
      loadResolved(),
      loadReadiness(),
    ]).then(function () {
      renderPanelHints();
    });
  }

  function selectedProviderId() {
    return value("manage-og-provider-select", "");
  }

  function selectedModelId() {
    return value("manage-og-model-select", "");
  }

  function selectedRouteId() {
    return value("manage-og-route-select", "");
  }

  function bindSelectionHydration() {
    var providerSelect = document.getElementById("manage-og-provider-select");
    if (providerSelect) {
      providerSelect.addEventListener("change", function () {
        var row = state.providers.find(function (p) { return p.provider_id === providerSelect.value; });
        if (!row) return;
        setValue("manage-og-provider-type", row.provider_type);
        setValue("manage-og-provider-display", row.display_name);
        setValue("manage-og-provider-base-url", row.base_url || "");
        setChecked("manage-og-provider-enabled", !!row.is_enabled);
        var pmeta = document.getElementById("manage-og-provider-meta");
        if (pmeta) {
          var pb = [];
          pb.push(row.is_enabled ? "Enabled" : "Disabled");
          pb.push("Health: " + (row.health_status || "unknown"));
          pb.push(row.eligible_for_runtime_assignment ? "Eligible for runtime assignment" : "Not eligible — fix limitations or credentials");
          if (row.limitations && row.limitations.length) {
            pb.push("Limitations: " + row.limitations.join(", "));
          }
          if (row.stage_support) pb.push("Stage support: " + row.stage_support);
          pmeta.textContent = pb.join(" · ");
        }
      });
    }

    var modelSelect = document.getElementById("manage-og-model-select");
    if (modelSelect) {
      modelSelect.addEventListener("change", function () {
        var row = state.models.find(function (m) { return m.model_id === modelSelect.value; });
        if (!row) return;
        setValue("manage-og-model-provider", row.provider_id);
        setValue("manage-og-model-name", row.model_name);
        setValue("manage-og-model-display", row.display_name);
        setValue("manage-og-model-role", row.model_role);
        setValue("manage-og-model-timeout", row.timeout_seconds || 30);
        setChecked("manage-og-model-structured", !!row.structured_output_capable);
        setChecked("manage-og-model-enabled", !!row.is_enabled);
        var mmeta = document.getElementById("manage-og-model-meta");
        if (mmeta) {
          var mb = [];
          mb.push(row.is_enabled ? "Enabled" : "Disabled");
          mb.push(row.runtime_eligible ? "Runtime-eligible" : "Not runtime-eligible for governed paths");
          if (row.provider_runtime_eligible === false) mb.push("Upstream provider is not runtime-eligible");
          if (row.readiness_blockers && row.readiness_blockers.length) {
            mb.push("Model blockers: " + row.readiness_blockers.join(", "));
          }
          mmeta.textContent = mb.join(" · ");
        }
      });
    }

    var routeSelect = document.getElementById("manage-og-route-select");
    if (routeSelect) {
      routeSelect.addEventListener("change", function () {
        var row = state.routes.find(function (r) { return r.route_id === routeSelect.value; });
        if (!row) return;
        setValue("manage-og-route-task-kind", row.task_kind);
        setValue("manage-og-route-workflow-scope", row.workflow_scope || "global");
        setValue("manage-og-route-preferred-model", row.preferred_model_id || "");
        setValue("manage-og-route-fallback-model", row.fallback_model_id || "");
        setValue("manage-og-route-mock-model", row.mock_model_id || "");
        setChecked("manage-og-route-enabled", !!row.is_enabled);
        setChecked("manage-og-route-use-mock", !!row.use_mock_when_provider_unavailable);
        var rmeta = document.getElementById("manage-og-route-meta");
        if (rmeta) {
          var rb = [];
          rb.push(row.is_enabled ? "Enabled" : "Disabled");
          rb.push(row.ai_path_ready ? "AI path resolves" : "AI path does not resolve — check models");
          rb.push(row.runtime_eligible ? "Eligible for governed runtime" : "Not eligible — adjust models or mock fallback");
          if (row.readiness_blockers && row.readiness_blockers.length) {
            rb.push("Route blockers: " + row.readiness_blockers.join(", "));
          }
          rmeta.textContent = rb.join(" · ");
        }
      });
    }
  }

  function bindActions() {
    var saveModesBtn = document.getElementById("manage-og-save-modes");
    if (saveModesBtn) {
      saveModesBtn.addEventListener("click", function () {
        var body = {
          generation_execution_mode: value("manage-og-generation-mode", "mock_only"),
          retrieval_execution_mode: value("manage-og-retrieval-mode", "disabled"),
          validation_execution_mode: value("manage-og-validation-mode", "schema_only"),
          provider_selection_mode: value("manage-og-provider-selection", "local_only"),
          runtime_profile: value("manage-og-runtime-profile", "safe_local"),
        };
        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/runtime/modes", {
          method: "PATCH",
          body: JSON.stringify(body),
        }).then(function () {
          return refreshAll({ preserveBanner: true }).then(function () {
            show("ok", "Runtime modes saved. Re-check readiness before promoting generation away from mock_only.");
          });
        }).catch(function (err) {
          show("err", parseError(err));
        });
      });
    }

    var reloadBtn = document.getElementById("manage-og-bootstrap-reload");
    if (reloadBtn) {
      reloadBtn.addEventListener("click", function () {
        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/runtime/reload-resolved-config", {
          method: "POST",
          body: "{}",
        }).then(function () {
          return refreshAll({ preserveBanner: true }).then(function () {
            show("ok", "Resolved configuration rebuilt from the database.");
          });
        }).catch(function (err) {
          show("err", parseError(err));
        });
      });
    }

    var providerCreateBtn = document.getElementById("manage-og-provider-create");
    if (providerCreateBtn) {
      providerCreateBtn.addEventListener("click", function () {
        var body = {
          provider_type: value("manage-og-provider-type", "mock"),
          display_name: value("manage-og-provider-display", "Provider"),
          base_url: value("manage-og-provider-base-url", ""),
          is_enabled: checked("manage-og-provider-enabled"),
        };
        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/providers", {
          method: "POST",
          body: JSON.stringify(body),
        }).then(function (res) {
          var pid = (res.data || {}).provider_id;
          var apiKey = value("manage-og-provider-api-key", "");
          if (!pid || !apiKey) return null;
          return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/providers/" + pid + "/credential", {
            method: "POST",
            body: JSON.stringify({ api_key: apiKey }),
          });
        }).then(function () {
          return refreshAll({ preserveBanner: true }).then(function () {
            show("ok", "Provider created.");
          });
        }).catch(function (err) {
          show("err", parseError(err));
        });
      });
    }

    var providerUpdateBtn = document.getElementById("manage-og-provider-update");
    if (providerUpdateBtn) {
      providerUpdateBtn.addEventListener("click", function () {
        var providerId = selectedProviderId();
        if (!providerId) {
          show("err", "Select a provider to update.");
          return;
        }
        var body = {
          provider_type: value("manage-og-provider-type", "mock"),
          display_name: value("manage-og-provider-display", "Provider"),
          base_url: value("manage-og-provider-base-url", ""),
          is_enabled: checked("manage-og-provider-enabled"),
        };
        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/providers/" + providerId, {
          method: "PATCH",
          body: JSON.stringify(body),
        }).then(function () {
          var apiKey = value("manage-og-provider-api-key", "");
          if (!apiKey) return null;
          return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/providers/" + providerId + "/credential", {
            method: "POST",
            body: JSON.stringify({ api_key: apiKey }),
          });
        }).then(function () {
          return refreshAll({ preserveBanner: true }).then(function () {
            show("ok", "Provider updated.");
          });
        }).catch(function (err) {
          show("err", parseError(err));
        });
      });
    }

    var providerTestBtn = document.getElementById("manage-og-provider-test");
    if (providerTestBtn) {
      providerTestBtn.addEventListener("click", function () {
        var providerId = selectedProviderId();
        if (!providerId) {
          show("err", "Select a provider to test.");
          return;
        }
        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/providers/" + providerId + "/test-connection", {
          method: "POST",
          body: "{}",
        }).then(function (res) {
          var data = res.data || {};
          return refreshAll({ preserveBanner: true }).then(function () {
            show("ok", "Provider test finished — health: " + (data.health_status || "unknown") + ".");
          });
        }).catch(function (err) {
          show("err", parseError(err));
        });
      });
    }

    var modelCreateBtn = document.getElementById("manage-og-model-create");
    if (modelCreateBtn) {
      modelCreateBtn.addEventListener("click", function () {
        var body = {
          provider_id: value("manage-og-model-provider", ""),
          model_name: value("manage-og-model-name", ""),
          display_name: value("manage-og-model-display", ""),
          model_role: value("manage-og-model-role", "llm"),
          supports_structured_output: checked("manage-og-model-structured"),
          timeout_seconds: parseInt(value("manage-og-model-timeout", "30"), 10) || 30,
          is_enabled: checked("manage-og-model-enabled"),
        };
        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/models", {
          method: "POST",
          body: JSON.stringify(body),
        }).then(function () {
          return refreshAll({ preserveBanner: true }).then(function () {
            show("ok", "Model created.");
          });
        }).catch(function (err) {
          show("err", parseError(err));
        });
      });
    }

    var modelUpdateBtn = document.getElementById("manage-og-model-update");
    if (modelUpdateBtn) {
      modelUpdateBtn.addEventListener("click", function () {
        var modelId = selectedModelId();
        if (!modelId) {
          show("err", "Select a model to update.");
          return;
        }
        var body = {
          display_name: value("manage-og-model-display", ""),
          model_role: value("manage-og-model-role", "llm"),
          structured_output_capable: checked("manage-og-model-structured"),
          timeout_seconds: parseInt(value("manage-og-model-timeout", "30"), 10) || 30,
          is_enabled: checked("manage-og-model-enabled"),
        };
        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/models/" + modelId, {
          method: "PATCH",
          body: JSON.stringify(body),
        }).then(function () {
          return refreshAll({ preserveBanner: true }).then(function () {
            show("ok", "Model updated.");
          });
        }).catch(function (err) {
          show("err", parseError(err));
        });
      });
    }

    var routeCreateBtn = document.getElementById("manage-og-route-create");
    if (routeCreateBtn) {
      routeCreateBtn.addEventListener("click", function () {
        var body = {
          task_kind: value("manage-og-route-task-kind", ""),
          workflow_scope: value("manage-og-route-workflow-scope", "global"),
          preferred_model_id: value("manage-og-route-preferred-model", "") || null,
          fallback_model_id: value("manage-og-route-fallback-model", "") || null,
          mock_model_id: value("manage-og-route-mock-model", "") || null,
          is_enabled: checked("manage-og-route-enabled"),
          use_mock_when_provider_unavailable: checked("manage-og-route-use-mock"),
        };
        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/routes", {
          method: "POST",
          body: JSON.stringify(body),
        }).then(function () {
          return refreshAll({ preserveBanner: true }).then(function () {
            show("ok", "Route created.");
          });
        }).catch(function (err) {
          show("err", parseError(err));
        });
      });
    }

    var routeUpdateBtn = document.getElementById("manage-og-route-update");
    if (routeUpdateBtn) {
      routeUpdateBtn.addEventListener("click", function () {
        var routeId = selectedRouteId();
        if (!routeId) {
          show("err", "Select a route to update.");
          return;
        }
        var body = {
          task_kind: value("manage-og-route-task-kind", ""),
          workflow_scope: value("manage-og-route-workflow-scope", "global"),
          preferred_model_id: value("manage-og-route-preferred-model", "") || null,
          fallback_model_id: value("manage-og-route-fallback-model", "") || null,
          mock_model_id: value("manage-og-route-mock-model", "") || null,
          is_enabled: checked("manage-og-route-enabled"),
          use_mock_when_provider_unavailable: checked("manage-og-route-use-mock"),
        };
        window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/routes/" + routeId, {
          method: "PATCH",
          body: JSON.stringify(body),
        }).then(function () {
          return refreshAll({ preserveBanner: true }).then(function () {
            show("ok", "Route updated.");
          });
        }).catch(function (err) {
          show("err", parseError(err));
        });
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.ManageAuth) return;
    window.ManageAuth.ensureAuth()
      .then(function () {
        bindSelectionHydration();
        bindActions();
        return refreshAll();
      })
      .catch(function (err) {
        show("err", parseError(err));
      });

    var refreshBtn = document.getElementById("manage-og-refresh");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        refreshAll().catch(function (err) {
          show("err", parseError(err));
        });
      });
    }
  });
})();
