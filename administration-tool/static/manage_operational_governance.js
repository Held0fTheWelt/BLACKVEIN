/**
 * AI Runtime Governance admin surface.
 */
(function () {
  var state = {
    providers: [],
    models: [],
    routes: [],
  };

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
      emptyOption.textContent = "—";
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

  function loadProviders() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/providers").then(function (res) {
      state.providers = (res.data || {}).providers || [];
      setSelectOptions("manage-og-provider-select", state.providers, "provider_id", function (p) {
        return p.provider_id + " (" + p.provider_type + ")";
      }, true);
      setSelectOptions("manage-og-model-provider", state.providers, "provider_id", function (p) {
        return p.provider_id + " (" + p.health_status + ")";
      }, false);
      setJson("manage-og-providers-json", { providers: state.providers });
    });
  }

  function loadModels() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/models").then(function (res) {
      state.models = (res.data || {}).models || [];
      setSelectOptions("manage-og-model-select", state.models, "model_id", function (m) {
        return m.model_id + " -> " + m.provider_id;
      }, true);
      setSelectOptions("manage-og-route-preferred-model", state.models, "model_id", function (m) {
        return m.model_id + " (" + m.model_role + ")";
      }, true);
      setSelectOptions("manage-og-route-fallback-model", state.models, "model_id", function (m) {
        return m.model_id + " (" + m.model_role + ")";
      }, true);
      setSelectOptions("manage-og-route-mock-model", state.models, "model_id", function (m) {
        return m.model_id + " (" + m.model_role + ")";
      }, true);
      setJson("manage-og-models-json", { models: state.models });
    });
  }

  function loadRoutes() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/routes").then(function (res) {
      state.routes = (res.data || {}).routes || [];
      setSelectOptions("manage-og-route-select", state.routes, "route_id", function (r) {
        return r.route_id + " [" + r.task_kind + "]";
      }, true);
      setJson("manage-og-routes-json", { routes: state.routes });
    });
  }

  function loadModes() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/runtime/modes").then(function (res) {
      var data = res.data || {};
      setValue("manage-og-generation-mode", data.generation_execution_mode);
      setValue("manage-og-retrieval-mode", data.retrieval_execution_mode);
      setValue("manage-og-validation-mode", data.validation_execution_mode);
      setValue("manage-og-provider-selection", data.provider_selection_mode);
      setValue("manage-og-runtime-profile", data.runtime_profile);
    });
  }

  function loadResolved() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/runtime/resolved-config").then(function (res) {
      setJson("manage-og-runtime-config", res.data || {});
    });
  }

  function loadReadiness() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/ai/runtime-readiness").then(function (res) {
      setJson("manage-og-readiness-json", res.data || {});
    });
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
    ]);
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
            show("ok", "Runtime modes updated.");
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
            show("ok", "Resolved config regenerated.");
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
            show("ok", "Provider health: " + (data.health_status || "unknown"));
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
