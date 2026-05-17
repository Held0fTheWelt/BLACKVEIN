/* Langfuse observability settings management */

(function () {
  "use strict";

  var currentConfig = null;
  var currentEnvelope = null;

  var refreshBtn = null;
  var saveConfigBtn = null;
  var saveCredentialBtn = null;
  var testConnBtn = null;
  var disableBtn = null;
  var banner = null;
  var success = null;
  var configJson = null;

  var enabledInput = null;
  var baseUrlInput = null;
  var environmentInput = null;
  var releaseInput = null;
  var sampleRateInput = null;
  var capturePromptsInput = null;
  var captureOutputsInput = null;
  var captureRetrievalInput = null;
  var redactionModeInput = null;
  var observationTreesInput = null;
  var observationTreesSelectedText = null;
  var observationTreesMinimalBtn = null;
  var observationTreesAllBtn = null;
  var observationTreesNoneBtn = null;

  var publicKeyInput = null;
  var secretKeyInput = null;
  var credentialStatus = null;

  var statusRow = null;
  var statusHeadline = null;
  var statusEnabled = null;
  var statusCredential = null;
  var statusHealth = null;
  var statusTested = null;

  function byId(id) {
    return document.getElementById(id);
  }

  function unwrapEnvelope(payload) {
    if (!payload || typeof payload !== "object") return {};
    if (Object.prototype.hasOwnProperty.call(payload, "data")) {
      return payload.data || {};
    }
    return payload;
  }

  function parseError(err) {
    if (!err) return "Request failed";
    if (typeof err.message === "string" && err.message.trim()) return err.message.trim();
    if (
      err.body &&
      window.ManageAuth &&
      typeof window.ManageAuth.formatApiErrorMessage === "function"
    ) {
      return window.ManageAuth.formatApiErrorMessage(err.body, err.status);
    }
    return "Request failed";
  }

  function serializeError(err) {
    var out = {
      message: parseError(err),
      status: err && typeof err.status === "number" ? err.status : 0,
    };
    if (err && Object.prototype.hasOwnProperty.call(err, "body")) {
      out.body = err.body;
    }
    return out;
  }

  function setTechnicalAudit(payload) {
    if (!configJson) return;
    configJson.textContent = JSON.stringify(payload || {}, null, 2);
  }

  function clearMessages() {
    if (banner) {
      banner.hidden = true;
      banner.textContent = "";
    }
    if (success) {
      success.hidden = true;
      success.textContent = "";
    }
  }

  function showError(msg, err, action) {
    clearMessages();
    if (banner) {
      banner.textContent = msg;
      banner.hidden = false;
    }
    if (typeof console !== "undefined" && typeof console.error === "function") {
      console.error("[manage_observability_settings] " + (action || "request") + " failed", err);
    }
  }

  function showSuccess(msg) {
    if (!success) return;
    success.textContent = msg;
    success.hidden = false;
  }

  function setElementRefs() {
    refreshBtn = byId("manage-obs-refresh");
    saveConfigBtn = byId("manage-obs-save-config");
    saveCredentialBtn = byId("manage-obs-save-credential");
    testConnBtn = byId("manage-obs-test-connection");
    disableBtn = byId("manage-obs-disable");
    banner = byId("manage-obs-banner");
    success = byId("manage-obs-success");
    configJson = byId("manage-obs-config-json");

    enabledInput = byId("manage-obs-enabled");
    baseUrlInput = byId("manage-obs-base-url");
    environmentInput = byId("manage-obs-environment");
    releaseInput = byId("manage-obs-release");
    sampleRateInput = byId("manage-obs-sample-rate");
    capturePromptsInput = byId("manage-obs-capture-prompts");
    captureOutputsInput = byId("manage-obs-capture-outputs");
    captureRetrievalInput = byId("manage-obs-capture-retrieval");
    redactionModeInput = byId("manage-obs-redaction-mode");
    observationTreesInput = byId("manage-obs-observation-trees");
    observationTreesSelectedText = byId("manage-obs-observation-trees-selected");
    observationTreesMinimalBtn = byId("manage-obs-trees-minimal");
    observationTreesAllBtn = byId("manage-obs-trees-all");
    observationTreesNoneBtn = byId("manage-obs-trees-none");

    publicKeyInput = byId("manage-obs-public-key");
    secretKeyInput = byId("manage-obs-secret-key");
    credentialStatus = byId("manage-obs-credential-status");

    statusRow = byId("manage-obs-status-row");
    statusHeadline = byId("manage-obs-status-headline");
    statusEnabled = byId("manage-obs-status-enabled");
    statusCredential = byId("manage-obs-status-credential");
    statusHealth = byId("manage-obs-status-health");
    statusTested = byId("manage-obs-status-tested");

    return !!(
      refreshBtn &&
      saveConfigBtn &&
      saveCredentialBtn &&
      testConnBtn &&
      disableBtn &&
      banner &&
      success &&
      configJson
    );
  }

  function defaultObservationTrees() {
    return ["minimal"];
  }

  function selectedObservationTrees() {
    if (!observationTreesInput) return defaultObservationTrees();
    return Array.prototype.slice.call(observationTreesInput.options)
      .filter(function (option) { return option.selected; })
      .map(function (option) { return option.value; });
  }

  function selectedObservationTreeLabels() {
    if (!observationTreesInput) return [];
    return Array.prototype.slice.call(observationTreesInput.options)
      .filter(function (option) { return option.selected; })
      .map(function (option) { return option.textContent || option.value; });
  }

  function updateObservationTreesSelectionSummary() {
    if (!observationTreesSelectedText) return;
    var labels = selectedObservationTreeLabels();
    if (!labels.length) {
      observationTreesSelectedText.textContent = "Selected: none (root trace only)";
      return;
    }
    observationTreesSelectedText.textContent = "Selected: " + labels.join(", ");
  }

  function setSelectedObservationTrees(values) {
    if (!observationTreesInput) return;
    var selected = {};
    (Array.isArray(values) ? values : defaultObservationTrees()).forEach(function (value) {
      selected[String(value)] = true;
    });
    Array.prototype.slice.call(observationTreesInput.options).forEach(function (option) {
      option.selected = !!selected[option.value];
    });
    updateObservationTreesSelectionSummary();
  }

  function allObservationTreeValues() {
    if (!observationTreesInput) return defaultObservationTrees();
    return Array.prototype.slice.call(observationTreesInput.options).map(function (option) {
      return option.value;
    });
  }

  function classToggle(node, className, value) {
    if (!node) return;
    if (value) node.classList.add(className);
    else node.classList.remove(className);
  }

  var HEALTH_POSITIVE = {
    connected: true,
    healthy: true,
  };

  var HEALTH_NEGATIVE = {
    unhealthy: true,
    auth_failed: true,
    credential_missing: true,
    credential_invalid: true,
    host_mismatch: true,
    export_failed: true,
    ingest_delayed: true,
    ingest_forbidden: true,
    usage_limit_exceeded: true,
    sdk_missing: true,
  };

  var HEALTH_LABELS = {
    connected: "Connected",
    healthy: "Healthy",
    unconfigured: "Unconfigured",
    disabled: "Disabled",
    unknown: "Unknown",
    unhealthy: "Unhealthy",
    auth_failed: "Auth failed",
    credential_missing: "Credential missing",
    credential_invalid: "Credential invalid",
    host_mismatch: "Host mismatch",
    export_failed: "Export failed",
    ingest_delayed: "Ingest delayed",
    ingest_forbidden: "Ingest forbidden",
    usage_limit_exceeded: "Usage limit exceeded",
    sdk_missing: "SDK missing",
  };

  function formatHealthStatus(status) {
    var key = (status || "unknown").toLowerCase();
    return HEALTH_LABELS[key] || status || "Unknown";
  }

  function resetStatusClasses() {
    classToggle(statusHeadline, "manage-obs-ok", false);
    classToggle(statusHeadline, "manage-obs-muted", false);
    classToggle(statusCredential, "manage-obs-danger-text", false);
    classToggle(statusHealth, "manage-obs-health-healthy", false);
    classToggle(statusHealth, "manage-obs-health-unhealthy", false);
    classToggle(statusHealth, "manage-obs-health-unknown", false);
  }

  function renderConfig() {
    if (!currentConfig) return;

    enabledInput.checked = !!currentConfig.is_enabled;
    baseUrlInput.value = currentConfig.base_url || "https://cloud.langfuse.com";
    environmentInput.value = currentConfig.environment || "development";
    releaseInput.value = currentConfig.release || "unknown";
    sampleRateInput.value = currentConfig.sample_rate == null ? 1.0 : currentConfig.sample_rate;
    capturePromptsInput.checked = currentConfig.capture_prompts !== false;
    captureOutputsInput.checked = currentConfig.capture_outputs !== false;
    captureRetrievalInput.checked = currentConfig.capture_retrieval === true;
    redactionModeInput.value = currentConfig.redaction_mode || "strict";
    setSelectedObservationTrees(currentConfig.enabled_observation_trees || defaultObservationTrees());

    if (currentConfig.credential_configured) {
      credentialStatus.textContent =
        "Configured (fingerprint: " + (currentConfig.credential_fingerprint || "unknown") + ")";
      classToggle(credentialStatus, "manage-obs-danger-text", false);
      classToggle(credentialStatus, "manage-obs-ok", true);
    } else {
      credentialStatus.textContent = "Not configured. Enter credentials to enable tracing.";
      classToggle(credentialStatus, "manage-obs-danger-text", true);
      classToggle(credentialStatus, "manage-obs-ok", false);
    }

    publicKeyInput.value = "";
    secretKeyInput.value = "";
  }

  function updateStatusDisplay() {
    if (!currentConfig) {
      statusRow.hidden = true;
      return;
    }

    statusRow.hidden = false;
    resetStatusClasses();

    if (currentConfig.is_enabled) {
      statusHeadline.textContent = "Langfuse is enabled";
      classToggle(statusHeadline, "manage-obs-ok", true);
    } else {
      statusHeadline.textContent = "Langfuse is disabled";
      classToggle(statusHeadline, "manage-obs-muted", true);
    }

    statusEnabled.textContent = currentConfig.is_enabled ? "Enabled" : "Disabled";

    if (currentConfig.credential_configured) {
      statusCredential.textContent = "Configured (" + (currentConfig.credential_fingerprint || "—") + ")";
    } else {
      statusCredential.textContent = "Not configured";
      classToggle(statusCredential, "manage-obs-danger-text", true);
    }

    var health = (currentConfig.health_status || "unknown").toLowerCase();
    statusHealth.textContent = formatHealthStatus(health);
    if (HEALTH_POSITIVE[health]) classToggle(statusHealth, "manage-obs-health-healthy", true);
    else if (HEALTH_NEGATIVE[health]) classToggle(statusHealth, "manage-obs-health-unhealthy", true);
    else classToggle(statusHealth, "manage-obs-health-unknown", true);

    if (currentConfig.last_tested_at) {
      var dt = new Date(currentConfig.last_tested_at);
      statusTested.textContent = Number.isNaN(dt.getTime())
        ? String(currentConfig.last_tested_at)
        : dt.toLocaleString();
    } else {
      statusTested.textContent = "Never tested";
    }

    var cardIds = [
      "manage-obs-status-enabled-card",
      "manage-obs-status-credential-card",
      "manage-obs-status-health-card",
      "manage-obs-status-tested-card",
    ];
    cardIds.forEach(function (id) {
      var pill = byId(id.replace("-card", ""));
      var card = byId(id);
      if (pill && card) card.textContent = pill.textContent;
    });
  }

  function api(path, opts) {
    if (!window.ManageAuth || typeof window.ManageAuth.apiFetchWithAuth !== "function") {
      return Promise.reject({ status: 0, message: "ManageAuth API bridge unavailable" });
    }
    return window.ManageAuth.apiFetchWithAuth(path, opts || {});
  }

  function setBusy(button, busyText, isBusy) {
    if (!button) return;
    if (isBusy) {
      button.dataset.originalText = button.textContent || "";
      button.disabled = true;
      if (busyText) button.textContent = busyText;
      return;
    }
    button.disabled = false;
    if (button.dataset.originalText) {
      button.textContent = button.dataset.originalText;
      delete button.dataset.originalText;
    }
  }

  async function loadConfig(suppressSuccess) {
    clearMessages();
    try {
      var response = await api("/api/v1/admin/observability/status");
      currentEnvelope = response || {};
      currentConfig = unwrapEnvelope(response);
      renderConfig();
      updateStatusDisplay();
      setTechnicalAudit({
        action: "status",
        loaded_at: new Date().toISOString(),
        envelope: currentEnvelope,
        config: currentConfig,
      });
      if (!suppressSuccess) showSuccess("Configuration loaded.");
    } catch (err) {
      setTechnicalAudit({
        action: "status",
        failed_at: new Date().toISOString(),
        error: serializeError(err),
      });
      showError("Failed to load configuration: " + parseError(err), err, "loadConfig");
    }
  }

  async function saveConfig() {
    clearMessages();
    var sampleRate = parseFloat(sampleRateInput.value);
    if (!Number.isFinite(sampleRate) || sampleRate < 0 || sampleRate > 1) {
      showError("Sample rate must be a number between 0.0 and 1.0.", null, "saveConfig");
      return;
    }

    var payload = {
      is_enabled: !!enabledInput.checked,
      base_url: (baseUrlInput.value || "").trim(),
      environment: environmentInput.value,
      release: (releaseInput.value || "").trim(),
      sample_rate: sampleRate,
      capture_prompts: !!capturePromptsInput.checked,
      capture_outputs: !!captureOutputsInput.checked,
      capture_retrieval: !!captureRetrievalInput.checked,
      redaction_mode: redactionModeInput.value,
      enabled_observation_trees: selectedObservationTrees(),
    };

    setBusy(saveConfigBtn, "Saving...", true);
    try {
      var response = await api("/api/v1/admin/observability/update", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await loadConfig(true);
      showSuccess("Configuration saved successfully.");
      setTechnicalAudit({
        action: "update",
        saved_at: new Date().toISOString(),
        request_payload: payload,
        response: response,
        current: currentConfig,
      });
    } catch (err) {
      setTechnicalAudit({
        action: "update",
        failed_at: new Date().toISOString(),
        request_payload: payload,
        error: serializeError(err),
      });
      showError("Failed to save configuration: " + parseError(err), err, "saveConfig");
    } finally {
      setBusy(saveConfigBtn, "", false);
    }
  }

  async function saveCredential() {
    clearMessages();
    var publicKey = (publicKeyInput.value || "").trim();
    var secretKey = (secretKeyInput.value || "").trim();

    if (!publicKey && !secretKey) {
      showError("At least one credential (public_key or secret_key) is required.", null, "saveCredential");
      return;
    }

    var payload = {};
    if (publicKey) payload.public_key = publicKey;
    if (secretKey) payload.secret_key = secretKey;

    setBusy(saveCredentialBtn, "Saving...", true);
    try {
      var response = await api("/api/v1/admin/observability/credential", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await loadConfig(true);

      var responseData = unwrapEnvelope(response);
      var fingerprints = [];
      if (responseData.public_key_fingerprint) fingerprints.push("pk: " + responseData.public_key_fingerprint);
      if (responseData.secret_key_fingerprint) fingerprints.push("sk: " + responseData.secret_key_fingerprint);

      var suffix = fingerprints.length ? " (" + fingerprints.join(", ") + ")" : "";
      showSuccess("Credentials saved successfully." + suffix);
      setTechnicalAudit({
        action: "credential",
        saved_at: new Date().toISOString(),
        response: response,
        current: currentConfig,
      });
    } catch (err) {
      setTechnicalAudit({
        action: "credential",
        failed_at: new Date().toISOString(),
        error: serializeError(err),
      });
      showError("Failed to save credentials: " + parseError(err), err, "saveCredential");
    } finally {
      setBusy(saveCredentialBtn, "", false);
    }
  }

  async function testConnection() {
    clearMessages();
    setBusy(testConnBtn, "Testing...", true);
    try {
      var response = await api("/api/v1/admin/observability/test-connection", {
        method: "POST",
        body: "{}",
      });
      await loadConfig(true);
      var details = unwrapEnvelope(response);
      var status = (details.health_status || "unknown").toLowerCase();
      var message = details.message || "No diagnostic message.";
      var shortMsg = message.length > 120 ? message.slice(0, 117) + "..." : message;
      showSuccess(
        "Connection test: " + formatHealthStatus(status) + " — " + shortMsg
      );
      setTechnicalAudit({
        action: "test_connection",
        tested_at: new Date().toISOString(),
        response: response,
        current: currentConfig,
      });
    } catch (err) {
      setTechnicalAudit({
        action: "test_connection",
        failed_at: new Date().toISOString(),
        error: serializeError(err),
      });
      showError("Connection test failed: " + parseError(err), err, "testConnection");
    } finally {
      setBusy(testConnBtn, "", false);
    }
  }

  async function disableObservability() {
    if (!window.confirm("Disable Langfuse observability? This will clear all configuration and credentials permanently.")) {
      return;
    }
    clearMessages();
    setBusy(disableBtn, "Disabling...", true);
    try {
      var response = await api("/api/v1/admin/observability/disable", {
        method: "DELETE",
      });
      await loadConfig(true);
      showSuccess("Langfuse observability disabled.");
      setTechnicalAudit({
        action: "disable",
        disabled_at: new Date().toISOString(),
        response: response,
        current: currentConfig,
      });
    } catch (err) {
      setTechnicalAudit({
        action: "disable",
        failed_at: new Date().toISOString(),
        error: serializeError(err),
      });
      showError("Failed to disable Langfuse: " + parseError(err), err, "disableObservability");
    } finally {
      setBusy(disableBtn, "", false);
    }
  }

  function bindActions() {
    refreshBtn.addEventListener("click", function () {
      loadConfig(false);
    });
    saveConfigBtn.addEventListener("click", saveConfig);
    saveCredentialBtn.addEventListener("click", saveCredential);
    testConnBtn.addEventListener("click", testConnection);
    disableBtn.addEventListener("click", disableObservability);
    if (observationTreesInput) {
      observationTreesInput.addEventListener("change", updateObservationTreesSelectionSummary);
    }
    if (observationTreesMinimalBtn) {
      observationTreesMinimalBtn.addEventListener("click", function () {
        setSelectedObservationTrees(defaultObservationTrees());
      });
    }
    if (observationTreesAllBtn) {
      observationTreesAllBtn.addEventListener("click", function () {
        setSelectedObservationTrees(allObservationTreeValues());
      });
    }
    if (observationTreesNoneBtn) {
      observationTreesNoneBtn.addEventListener("click", function () {
        setSelectedObservationTrees([]);
      });
    }
  }

  function init() {
    if (!setElementRefs()) {
      if (typeof console !== "undefined" && typeof console.error === "function") {
        console.error("[manage_observability_settings] Required DOM elements missing.");
      }
      return;
    }
    if (!window.ManageAuth) {
      showError("Manage authentication helper is unavailable.", null, "init");
      return;
    }
    window.ManageAuth
      .ensureAuth()
      .then(function () {
        bindActions();
        return loadConfig(false);
      })
      .catch(function (err) {
        showError("Authentication check failed: " + parseError(err), err, "initAuth");
      });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
