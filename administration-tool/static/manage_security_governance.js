(function () {
  "use strict";

  var ENDPOINT = "/api/v1/admin/security/governance";
  var currentPayload = null;

  function byId(id) {
    return document.getElementById(id);
  }

  function unwrap(payload) {
    if (!payload || typeof payload !== "object") return {};
    if (Object.prototype.hasOwnProperty.call(payload, "data")) return payload.data || {};
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

  function setText(id, value) {
    var el = byId(id);
    if (el) el.textContent = value == null || value === "" ? "-" : String(value);
  }

  function setMessage(message, isError) {
    var error = byId("manage-sg-error");
    var success = byId("manage-sg-success");
    var result = byId("manage-sg-result");
    if (error) {
      error.hidden = true;
      error.textContent = "";
    }
    if (success) {
      success.hidden = true;
      success.textContent = "";
    }
    if (result) {
      result.hidden = true;
      result.textContent = "";
    }
    if (isError && error) {
      error.hidden = false;
      error.textContent = message;
      return;
    }
    if (!isError && success) {
      success.hidden = false;
      success.textContent = message;
    }
    if (!isError && result) {
      result.hidden = false;
      result.textContent = message;
    }
  }

  function setChecked(id, value) {
    var el = byId(id);
    if (el) el.checked = !!value;
  }

  function setValue(id, value) {
    var el = byId(id);
    if (el) el.value = value == null ? "" : String(value);
  }

  function addListItem(list, label, value) {
    if (!list) return;
    var li = document.createElement("li");
    var strong = document.createElement("strong");
    strong.textContent = label;
    li.appendChild(strong);
    li.appendChild(document.createTextNode(": " + (value == null || value === "" ? "-" : String(value))));
    list.appendChild(li);
  }

  function yesNo(value) {
    return value ? "yes" : "no";
  }

  function renderList(id, items, emptyText) {
    var list = byId(id);
    if (!list) return;
    list.innerHTML = "";
    if (!items || !items.length) {
      var li = document.createElement("li");
      li.textContent = emptyText || "None";
      list.appendChild(li);
      return;
    }
    items.forEach(function (item) {
      var li = document.createElement("li");
      li.textContent = String(item);
      list.appendChild(li);
    });
  }

  function renderEffective(effective) {
    var list = byId("manage-sg-effective-list");
    if (!list) return;
    list.innerHTML = "";
    var cookie = (effective && effective.backend_session_cookie) || {};
    var csrf = (effective && effective.backend_csrf) || {};
    var api = (effective && effective.json_api_auth) || {};
    var proxy = (effective && effective.same_origin_proxies) || {};
    addListItem(list, "Session cookie Secure", cookie.secure ? "yes" : "no");
    addListItem(list, "Session cookie HttpOnly", cookie.httponly ? "yes" : "no");
    addListItem(list, "Session cookie SameSite", cookie.samesite || "-");
    addListItem(list, "API v1 CSRF exemption", csrf.api_v1_exempt ? "code-owned" : "disabled");
    addListItem(list, "JSON API credential", api.expected_credential || "-");
    addListItem(list, "Admin proxy forwards cookies", proxy.admin_proxy_cookie_forwarding_allowed ? "yes" : "no");
  }

  function renderSecretGovernance(secret) {
    var list = byId("manage-sg-secret-governance");
    if (!list) return;
    list.innerHTML = "";
    var local = (secret && secret.local_bootstrap) || {};
    var prod = (secret && secret.production) || {};
    addListItem(list, "Local source", local.source || "repo-root .env");
    addListItem(list, "Local Docker-Up preserved", local.preserved ? "yes" : "no");
    addListItem(list, "Production required", prod.required ? "yes" : "no");
    addListItem(list, "Production mode", prod.mode || "-");
    addListItem(list, "Provider", prod.provider || "-");
    addListItem(list, "Rotation interval", prod.rotation_interval_days ? prod.rotation_interval_days + " days" : "-");
    addListItem(list, "Audit required", prod.audit_required ? "yes" : "no");
    addListItem(list, "Access separation", prod.access_separation_required ? "yes" : "no");
    if (local.rule) addListItem(list, "Invariant", local.rule);
  }

  function renderRedisGovernance(redis) {
    var posture = byId("manage-sg-redis-effective-list");
    var observed = (redis && redis.observed) || {};
    var backend = observed.backend_redis_url || {};
    var app = observed.app_redis_url || {};
    var langfuse = observed.langfuse_redis_connection || {};
    if (posture) {
      posture.innerHTML = "";
      addListItem(posture, "Profile", redis && redis.profile);
      addListItem(posture, "Status", redis && redis.status);
      addListItem(posture, "Backend Redis scheme", backend.scheme || "-");
      addListItem(posture, "App Redis scheme", app.scheme || "-");
      addListItem(posture, "Langfuse Redis scheme", langfuse.scheme || "-");
      addListItem(posture, "TLS ready", yesNo(observed.tls_ready));
      addListItem(posture, "ACL ready", yesNo(observed.acl_ready));
      addListItem(posture, "Separate hosts", yesNo(observed.separate_hosts));
      addListItem(posture, "No host ports expected", yesNo(observed.no_host_ports_expected));
      addListItem(posture, "Compose override", redis && redis.compose_override);
      addListItem(posture, "Generated assets", redis && redis.generated_asset_root);
    }

    var checks = ((redis && redis.checks) || []).map(function (check) {
      var state = check.pass ? "PASS" : "ATTENTION";
      var required = check.required ? "required" : "optional";
      return state + " (" + required + "): " + check.label + " - " + (check.detail || "-");
    });
    renderList("manage-sg-redis-checks", checks, "No Redis checks returned.");
    renderList("manage-sg-redis-commands", (redis && redis.commands) || [], "No Redis commands returned.");
  }

  function renderStorageGovernance(storage) {
    var posture = byId("manage-sg-storage-effective-list");
    var coverage = (storage && storage.coverage) || {};
    if (posture) {
      posture.innerHTML = "";
      addListItem(posture, "Profile", storage && storage.profile);
      addListItem(posture, "Status", storage && storage.status);
      addListItem(posture, "Surfaces", String(coverage.complete_surface_count || 0) + " / " + String(coverage.surface_count || 0));
      addListItem(posture, "Evidenced surfaces", coverage.evidenced_surface_count || 0);
      addListItem(posture, "Verified surfaces", coverage.verified_surface_count || 0);
      addListItem(posture, "Failed required checks", coverage.failed_required_check_count || 0);
      ((storage && storage.surfaces) || []).forEach(function (surface) {
        var state = surface.pass ? "PASS" : "ATTENTION";
        var detail = surface.control_type || surface.status || "-";
        addListItem(posture, state + " " + surface.id, detail);
      });
    }

    var checks = ((storage && storage.checks) || []).map(function (check) {
      var state = check.pass ? "PASS" : "ATTENTION";
      var required = check.required ? "required" : "optional";
      return state + " (" + required + "): " + check.label + " - " + (check.detail || "-");
    });
    renderList("manage-sg-storage-checks", checks, "No storage checks returned.");
  }

  function renderMatrix(rows) {
    var body = byId("manage-sg-csrf-matrix");
    if (!body) return;
    body.innerHTML = "";
    (rows || []).forEach(function (row) {
      var tr = document.createElement("tr");
      ["flow", "credential", "mutation", "policy", "test"].forEach(function (key) {
        var td = document.createElement("td");
        td.textContent = row && row[key] ? String(row[key]) : "-";
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    if (!body.children.length) {
      var empty = document.createElement("tr");
      var cell = document.createElement("td");
      cell.colSpan = 5;
      cell.textContent = "No CSRF matrix rows returned.";
      empty.appendChild(cell);
      body.appendChild(empty);
    }
  }

  function renderJson(payload) {
    var pre = byId("manage-sg-json");
    if (pre) pre.textContent = JSON.stringify(payload || {}, null, 2);
  }

  function render(payload) {
    currentPayload = payload || {};
    var settings = currentPayload.settings || {};
    var effective = currentPayload.effective_posture || {};
    var redis = currentPayload.redis_governance || {};
    var storage = currentPayload.storage_encryption_governance || {};
    var cookie = effective.backend_session_cookie || {};

    setText("manage-sg-review-status", settings.review_status || "-");
    setText("manage-sg-target-samesite", settings.target_session_samesite || "-");
    setText("manage-sg-effective-samesite", cookie.samesite || "-");
    setText("manage-sg-secret-store-mode", settings.secret_store_mode || "-");
    setText("manage-sg-docker-up", settings.preserve_docker_up_local_bootstrap ? "preserved" : "not preserved");
    setText("manage-sg-redis-profile", settings.redis_hardening_profile || redis.profile || "-");
    setText("manage-sg-redis-status", redis.status || "-");
    setText("manage-sg-storage-status", storage.status || "-");

    setValue("manage-sg-field-review-status", settings.review_status || "approved");
    setValue("manage-sg-field-target-samesite", settings.target_session_samesite || "Lax");
    setValue("manage-sg-field-secret-store-mode", settings.secret_store_mode || "production_secret_store");
    setValue("manage-sg-field-secret-store-provider", settings.secret_store_provider || "deployment_managed");
    setValue("manage-sg-field-secret-rotation-days", settings.secret_rotation_interval_days || 90);
    setChecked("manage-sg-field-web-csrf", settings.require_backend_web_csrf);
    setChecked("manage-sg-field-bearer-api", settings.require_bearer_for_json_api);
    setChecked("manage-sg-field-proxy-cookie", settings.require_proxy_cookie_stripping);
    setChecked("manage-sg-field-regression-tests", settings.require_csrf_regression_tests);
    setChecked("manage-sg-field-secret-store", settings.production_secret_store_required);
    setChecked("manage-sg-field-secret-audit", settings.secret_store_audit_required);
    setChecked("manage-sg-field-secret-access-separation", settings.secret_store_access_separation_required);
    setChecked("manage-sg-field-preserve-docker-up", settings.preserve_docker_up_local_bootstrap);
    setValue("manage-sg-field-redis-profile", settings.redis_hardening_profile || "production_compose");
    setChecked("manage-sg-field-redis-hardening", settings.require_production_redis_hardening);
    setChecked("manage-sg-field-redis-tls", settings.require_redis_tls);
    setChecked("manage-sg-field-redis-acl", settings.require_redis_acl_users);
    setChecked("manage-sg-field-redis-separate", settings.require_redis_instance_separation);
    setChecked("manage-sg-field-redis-no-host-ports", settings.require_redis_no_host_ports);
    setChecked("manage-sg-field-redis-validation", settings.require_redis_validation_gate);
    setValue("manage-sg-field-storage-profile", settings.storage_encryption_profile || "mixed_evidence_pack");
    setChecked("manage-sg-field-storage-evidence-required", settings.require_storage_encryption_evidence);
    setChecked("manage-sg-field-backup-evidence-required", settings.require_backup_encryption_evidence);
    setChecked("manage-sg-field-storage-key-custody", settings.require_storage_key_custody_evidence);
    setChecked("manage-sg-field-storage-restore-test", settings.require_storage_restore_test_evidence);
    setValue(
      "manage-sg-field-storage-evidence-json",
      JSON.stringify(settings.storage_encryption_evidence || {}, null, 2)
    );
    setValue("manage-sg-field-notes", settings.operator_notes || "");

    renderEffective(effective);
    renderSecretGovernance(currentPayload.secret_management_governance || {});
    renderRedisGovernance(redis);
    renderStorageGovernance(storage);
    renderList("manage-sg-warnings", currentPayload.warnings || [], "No active warnings.");
    renderList("manage-sg-boundaries", currentPayload.non_editable_boundaries || [], "No boundaries returned.");
    renderMatrix(currentPayload.csrf_matrix || []);
    renderJson(currentPayload);
  }

  function readPayload() {
    var evidenceRaw = ((byId("manage-sg-field-storage-evidence-json") || {}).value || "").trim();
    var storageEvidence = {};
    if (evidenceRaw) {
      storageEvidence = JSON.parse(evidenceRaw);
      if (!storageEvidence || typeof storageEvidence !== "object" || Array.isArray(storageEvidence)) {
        throw new Error("Storage evidence JSON must be an object.");
      }
    }
    return {
      review_status: (byId("manage-sg-field-review-status") || {}).value || "approved",
      target_session_samesite: (byId("manage-sg-field-target-samesite") || {}).value || "Lax",
      require_backend_web_csrf: !!((byId("manage-sg-field-web-csrf") || {}).checked),
      require_bearer_for_json_api: !!((byId("manage-sg-field-bearer-api") || {}).checked),
      require_proxy_cookie_stripping: !!((byId("manage-sg-field-proxy-cookie") || {}).checked),
      require_csrf_regression_tests: !!((byId("manage-sg-field-regression-tests") || {}).checked),
      production_secret_store_required: !!((byId("manage-sg-field-secret-store") || {}).checked),
      secret_store_mode: (byId("manage-sg-field-secret-store-mode") || {}).value || "production_secret_store",
      secret_store_provider: (byId("manage-sg-field-secret-store-provider") || {}).value || "deployment_managed",
      secret_rotation_interval_days: Number((byId("manage-sg-field-secret-rotation-days") || {}).value || 90),
      secret_store_audit_required: !!((byId("manage-sg-field-secret-audit") || {}).checked),
      secret_store_access_separation_required: !!((byId("manage-sg-field-secret-access-separation") || {}).checked),
      preserve_docker_up_local_bootstrap: !!((byId("manage-sg-field-preserve-docker-up") || {}).checked),
      redis_hardening_profile: (byId("manage-sg-field-redis-profile") || {}).value || "production_compose",
      require_production_redis_hardening: !!((byId("manage-sg-field-redis-hardening") || {}).checked),
      require_redis_tls: !!((byId("manage-sg-field-redis-tls") || {}).checked),
      require_redis_acl_users: !!((byId("manage-sg-field-redis-acl") || {}).checked),
      require_redis_instance_separation: !!((byId("manage-sg-field-redis-separate") || {}).checked),
      require_redis_no_host_ports: !!((byId("manage-sg-field-redis-no-host-ports") || {}).checked),
      require_redis_validation_gate: !!((byId("manage-sg-field-redis-validation") || {}).checked),
      storage_encryption_profile: (byId("manage-sg-field-storage-profile") || {}).value || "mixed_evidence_pack",
      require_storage_encryption_evidence: !!((byId("manage-sg-field-storage-evidence-required") || {}).checked),
      require_backup_encryption_evidence: !!((byId("manage-sg-field-backup-evidence-required") || {}).checked),
      require_storage_key_custody_evidence: !!((byId("manage-sg-field-storage-key-custody") || {}).checked),
      require_storage_restore_test_evidence: !!((byId("manage-sg-field-storage-restore-test") || {}).checked),
      storage_encryption_evidence: storageEvidence,
      operator_notes: (byId("manage-sg-field-notes") || {}).value || "",
    };
  }

  function api(path, opts) {
    if (!window.ManageAuth || typeof window.ManageAuth.apiFetchWithAuth !== "function") {
      return Promise.reject(new Error("ManageAuth bridge unavailable"));
    }
    return window.ManageAuth.apiFetchWithAuth(path, opts).then(unwrap);
  }

  function load() {
    setMessage("Loading security governance...", false);
    return api(ENDPOINT).then(function (payload) {
      render(payload);
      setMessage("Security governance loaded.", false);
      return payload;
    }).catch(function (err) {
      setMessage("Security governance load failed: " + parseError(err), true);
    });
  }

  function save() {
    var payload;
    try {
      payload = readPayload();
    } catch (err) {
      setMessage("Security governance save failed: " + parseError(err), true);
      return Promise.resolve();
    }
    setMessage("Saving security governance...", false);
    return api(ENDPOINT, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }).then(function (updated) {
      render(updated);
      setMessage("Security governance saved.", false);
      return updated;
    }).catch(function (err) {
      setMessage("Security governance save failed: " + parseError(err), true);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!document.querySelector('[data-page="security-governance"]')) return;
    var refresh = byId("manage-sg-refresh");
    var saveBtn = byId("manage-sg-save");
    if (refresh) refresh.addEventListener("click", load);
    if (saveBtn) saveBtn.addEventListener("click", save);
    if (!window.ManageAuth || typeof window.ManageAuth.ensureAuth !== "function") {
      setMessage("ManageAuth unavailable.", true);
      return;
    }
    window.ManageAuth.ensureAuth().then(load).catch(function (err) {
      setMessage("Auth check failed: " + parseError(err), true);
    });
  });
})();
