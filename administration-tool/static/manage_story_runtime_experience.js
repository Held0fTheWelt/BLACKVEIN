// Story Runtime Experience operator controls — Administration Tool JS.
// Loaded alongside manage_runtime_settings.js on the Runtime Settings page.
(function () {
  if (!window.ManageAuth) return;

  var FIELD_IDS = {
    experience_mode: "manage-sre-experience-mode",
    delivery_profile: "manage-sre-delivery-profile",
    prose_density: "manage-sre-prose-density",
    explanation_level: "manage-sre-explanation-level",
    narrator_presence: "manage-sre-narrator-presence",
    dialogue_priority: "manage-sre-dialogue-priority",
    action_visibility: "manage-sre-action-visibility",
    repetition_guard: "manage-sre-repetition-guard",
    motif_handling: "manage-sre-motif-handling",
    npc_verbosity: "manage-sre-npc-verbosity",
    npc_initiative: "manage-sre-npc-initiative",
    inter_npc_exchange_intensity: "manage-sre-exchange-intensity",
    pulse_length: "manage-sre-pulse-length",
    max_scene_pulses_per_response: "manage-sre-max-pulses",
    allow_scene_progress_without_player_action: "manage-sre-allow-auto-progress",
    beat_progression_speed: "manage-sre-beat-speed"
  };

  function show(kind, msg) {
    var err = document.getElementById("manage-sre-banner");
    var ok = document.getElementById("manage-sre-success");
    if (err) { err.style.display = "none"; err.textContent = ""; }
    if (ok) { ok.style.display = "none"; ok.textContent = ""; }
    if (!msg) return;
    if (kind === "ok" && ok) { ok.style.display = ""; ok.textContent = msg; return; }
    if (err) { err.style.display = ""; err.textContent = msg; }
  }

  function parseError(err) {
    if (!err) return "Unknown error.";
    if (err.body && err.body.message) return err.body.message;
    if (err.message) return err.message;
    return String(err);
  }

  function setField(key, value) {
    var el = document.getElementById(FIELD_IDS[key]);
    if (!el) return;
    if (el.type === "checkbox") { el.checked = !!value; return; }
    if (value === null || value === undefined) return;
    el.value = String(value);
  }

  function readField(key) {
    var el = document.getElementById(FIELD_IDS[key]);
    if (!el) return undefined;
    if (el.type === "checkbox") return el.checked;
    if (el.type === "number") {
      var n = parseInt(el.value, 10);
      return isNaN(n) ? undefined : n;
    }
    return el.value;
  }

  function applyConfigured(configured) {
    if (!configured || typeof configured !== "object") return;
    Object.keys(FIELD_IDS).forEach(function (key) { setField(key, configured[key]); });
  }

  function renderTruthSurface(truth) {
    var honored = document.getElementById("manage-sre-mode-honored");
    if (honored) {
      honored.textContent = truth.experience_mode_honored_fully
        ? "Mode is fully honored by the runtime."
        : "Mode is partially honored — see degradation markers below.";
    }
    var degUl = document.getElementById("manage-sre-degradation-lines");
    if (degUl) {
      degUl.innerHTML = "";
      var markers = truth.degradation_markers || [];
      if (!markers.length) {
        var none = document.createElement("li");
        none.textContent = "No runtime degradation — configured == effective.";
        degUl.appendChild(none);
      } else {
        markers.forEach(function (m) {
          var li = document.createElement("li");
          li.textContent = (m.marker || "?") + " — " + (m.reason || "");
          degUl.appendChild(li);
        });
      }
    }
    var warnUl = document.getElementById("manage-sre-warning-lines");
    if (warnUl) {
      warnUl.innerHTML = "";
      var warnings = truth.validation_warnings || [];
      if (!warnings.length) {
        var noneW = document.createElement("li");
        noneW.textContent = "No validation warnings.";
        warnUl.appendChild(noneW);
      } else {
        warnings.forEach(function (w) {
          var li = document.createElement("li");
          li.textContent = String(w);
          warnUl.appendChild(li);
        });
      }
    }
    var effUl = document.getElementById("manage-sre-effective-lines");
    if (effUl) {
      effUl.innerHTML = "";
      var eff = truth.effective || {};
      Object.keys(eff).forEach(function (k) {
        var li = document.createElement("li");
        li.textContent = k + ": " + JSON.stringify(eff[k]);
        effUl.appendChild(li);
      });
      var contract = document.createElement("li");
      contract.textContent = "packaging_contract_version: " + (truth.packaging_contract_version || "—");
      effUl.appendChild(contract);
    }
    var pre = document.getElementById("manage-sre-json");
    if (pre) pre.textContent = JSON.stringify(truth, null, 2);
  }

  function collectPayload() {
    var payload = {};
    Object.keys(FIELD_IDS).forEach(function (key) {
      var v = readField(key);
      if (v !== undefined) payload[key] = v;
    });
    return payload;
  }

  function refresh() {
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/story-runtime-experience")
      .then(function (res) {
        var truth = (res && res.data) || res || {};
        applyConfigured(truth.configured || {});
        renderTruthSurface(truth);
      });
  }

  function save() {
    var payload = collectPayload();
    return window.ManageAuth.apiFetchWithAuth("/api/v1/admin/story-runtime-experience", {
      method: "PUT",
      body: JSON.stringify(payload)
    }).then(function (res) {
      var truth = (res && res.data) || res || {};
      applyConfigured(truth.configured || {});
      renderTruthSurface(truth);
      var warns = truth.update_warnings || [];
      if (warns.length) {
        show("err", "Saved with warnings: " + warns.join(" | "));
      } else {
        show("ok", "Story Runtime Experience saved.");
      }
    }).catch(function (err) {
      show("err", parseError(err));
    });
  }

  function bind() {
    var saveBtn = document.getElementById("manage-sre-save");
    if (saveBtn) saveBtn.addEventListener("click", function () { show(null, ""); save(); });
    var refreshBtn = document.getElementById("manage-sre-refresh");
    if (refreshBtn) refreshBtn.addEventListener("click", function () {
      show(null, "");
      refresh().catch(function (err) { show("err", parseError(err)); });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    window.ManageAuth.ensureAuth().then(function () {
      bind();
      return refresh();
    }).catch(function (err) { show("err", parseError(err)); });
  });
})();
