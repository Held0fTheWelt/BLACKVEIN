(function () {
  "use strict";

  function load(sessionId) {
    var params = sessionId ? { session_id: sessionId } : {};
    Promise.all([
      WorldEngineUI.apiFetch("admin/narrative/runtime/gov-summary"),
      WorldEngineUI.apiFetch(WorldEngineUI.buildUrl("admin/governance/narrative-systems", params)),
    ])
      .then(function (parts) {
        WorldEngineUI.renderJson("ui-narr-gov", parts[0]);
        WorldEngineUI.renderJson("ui-narr-systems", parts[1]);
      })
      .catch(function (err) {
        WorldEngineUI.setBanner("ui-page-banner", err.message || String(err), true);
      });

    if (!sessionId) {
      WorldEngineUI.renderJson("ui-narr-thin-path", {
        note: "Select a session to load thin-path diagnostics.",
      });
      return;
    }

    var base =
      "admin/world-engine/story/sessions/" + encodeURIComponent(sessionId);

    WorldEngineUI.apiFetch(base + "/runtime-diagnostic-snapshot?thin_path_limit=20")
      .then(function (snapshot) {
        renderSnapshotSections(snapshot);
        WorldEngineUI.renderJson("ui-narr-snapshot-raw", snapshot);
      })
      .catch(function (err) {
        WorldEngineUI.renderJson("ui-narr-snapshot-raw", {
          error: err.message || String(err),
        });
      });

    WorldEngineUI.apiFetch(base + "/thin-path-summary?limit=20")
      .then(function (summary) {
        WorldEngineUI.renderJson("ui-narr-thin-path", summary);
      })
      .catch(function (err) {
        WorldEngineUI.renderJson("ui-narr-thin-path", {
          error: err.message || String(err),
        });
        WorldEngineUI.setBanner("ui-page-banner", err.message || String(err), true);
      });
  }

  function renderSnapshotSections(snapshot) {
    var host = document.getElementById("ui-narr-snapshot-sections");
    if (!host) {
      return;
    }
    host.innerHTML = "";
    var sections = [
      { title: "Resolver", key: "resolver_output" },
      { title: "Canonical path hold", key: "canonical_path_hold_effect" },
      { title: "Narrator consequence", key: "narrator_consequence_realization" },
      { title: "Director gathering pause", key: "director_gathering_state" },
      { title: "Director pulse", key: "pulse" },
      { title: "NPC motivation scores", key: "npc_motivation_scores", fromPulse: true },
      { title: "Bundle vs event parity", key: "bundle_vs_event_stream_parity" },
    ];
    sections.forEach(function (sec) {
      var block = snapshot[sec.key];
      var payload = null;
      var notWired = true;
      if (sec.fromPulse && snapshot.pulse && !snapshot.pulse.not_yet_wired) {
        var pulse = snapshot.pulse.payload || {};
        payload = pulse.npc_motivation_scores || pulse.motivation_scores || null;
        notWired = payload == null;
      } else if (block) {
        notWired = !!block.not_yet_wired;
        payload = block.payload;
      }
      var card = document.createElement("article");
      card.className = "ui-card ui-card--compact";
      var h = document.createElement("h3");
      h.textContent = sec.title;
      card.appendChild(h);
      var pre = document.createElement("pre");
      pre.className = "ui-code";
      if (!block && !sec.fromPulse) {
        pre.textContent = "(missing)";
      } else if (notWired) {
        pre.textContent = "not_yet_wired: true";
      } else {
        pre.textContent = JSON.stringify(payload, null, 2);
      }
      card.appendChild(pre);
      host.appendChild(card);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    WorldEngineSession.bindSessionPicker(load);
    WorldEngineSession.loadSessionOptions();
    load(WorldEngineSession.selectedSessionId());
  });
})();
