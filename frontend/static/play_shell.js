(function () {
  const shell = document.querySelector(".play-shell");
  if (!shell) return;

  var showPlayDiagnostics = false;

  function escapeHtml(value) {
    const d = document.createElement("div");
    d.textContent = value == null ? "" : String(value);
    return d.innerHTML;
  }

  function normalizeLine(line) {
    if (line == null) return "";
    if (typeof line === "string") return line.trim();
    if (typeof line === "object") {
      const text = String(line.text || "").trim();
      if (!text) return "";
      const actor = String(line.speaker_id || line.actor_id || "").trim();
      const tone = String(line.tone || "").trim();
      const prefix = actor ? actor + ": " : "";
      const suffix = tone ? " (" + tone + ")" : "";
      return (prefix + text + suffix).trim();
    }
    return String(line).trim();
  }

  function normalizeEntry(entry) {
    const normalized = Object.assign({}, entry || {});
    normalized.role = String(normalized.role || "runtime").trim() || "runtime";
    normalized.speaker = normalized.speaker || (normalized.role === "player" ? "You" : "World of Shadows");
    normalized.text = String(normalized.text || "").trim();

    const spoken = Array.isArray(normalized.spoken_lines) ? normalized.spoken_lines : [];
    normalized.spoken_lines = spoken.map(normalizeLine).filter(Boolean);

    const action = Array.isArray(normalized.action_lines) ? normalized.action_lines : [];
    normalized.action_lines = action.map(normalizeLine).filter(Boolean);

    const consequences = Array.isArray(normalized.committed_consequences) ? normalized.committed_consequences : [];
    normalized.committed_consequences = consequences.map(normalizeLine).filter(Boolean);

    const reasons = Array.isArray(normalized.degraded_reasons) ? normalized.degraded_reasons : [];
    normalized.degraded_reasons = reasons.map(normalizeLine).filter(Boolean);
    normalized.degraded = Boolean(normalized.degraded);
    normalized.responder_id = String(normalized.responder_id || "").trim();
    normalized.validation_status = String(normalized.validation_status || "").trim();
    normalized.quality_class = String(normalized.quality_class || "").trim();
    normalized.degradation_summary = String(normalized.degradation_summary || "").trim();

    normalized.display_passivity_line = String(normalized.display_passivity_line || "").trim();
    normalized.display_vitality_line = String(normalized.display_vitality_line || "").trim();
    normalized.display_actor_turn_line = String(normalized.display_actor_turn_line || "").trim();
    normalized.display_render_support_warning = String(normalized.display_render_support_warning || "").trim();
    normalized.display_dramatic_context_compact = String(normalized.display_dramatic_context_compact || "").trim();
    const ditems = normalized.display_dramatic_context_items;
    normalized.display_dramatic_context_items = Array.isArray(ditems)
      ? ditems
          .filter(function (row) {
            return row && typeof row === "object";
          })
          .map(function (row) {
            return {
              key: String(row.key || "").trim(),
              label: String(row.label || "").trim(),
              value: String(row.value || "").trim(),
            };
          })
          .filter(function (row) {
            return row.label && row.value;
          })
      : [];

    return normalized;
  }

  function storyPlaceholderHtml() {
    return (
      '<p id="transcript-empty" class="play-story-placeholder">' +
      "No authored opening was returned by the story runtime. The player session is not ready for meaningful play." +
      "</p>"
    );
  }

  function runtimeDiagnosticsBlockHtml(entry, diagDeep) {
    if (entry.role !== "runtime") return "";
    let block = "";
    if (entry.display_render_support_warning) {
      block +=
        '<p class="play-runtime-warn">' + escapeHtml(entry.display_render_support_warning) + "</p>";
    }
    if (entry.display_passivity_line) {
      block +=
        '<p class="runtime-meta play-runtime-diagnostics__line">' + escapeHtml(entry.display_passivity_line) + "</p>";
    }
    if (entry.display_vitality_line) {
      block +=
        '<p class="runtime-meta play-runtime-diagnostics__line">' + escapeHtml(entry.display_vitality_line) + "</p>";
    }
    if (entry.display_actor_turn_line) {
      block +=
        '<p class="runtime-meta play-runtime-diagnostics__line">' + escapeHtml(entry.display_actor_turn_line) + "</p>";
    }
    if (entry.display_dramatic_context_compact) {
      block +=
        '<p class="runtime-meta play-runtime-diagnostics__line">' +
        escapeHtml(entry.display_dramatic_context_compact) +
        "</p>";
    }
    if (diagDeep && entry.display_dramatic_context_items.length) {
      block += '<details class="play-runtime-diagnostics__details">';
      block += '<summary class="runtime-meta">Dramatic context (diagnostics)</summary>';
      block += '<dl class="play-runtime-diagnostics__dl">';
      entry.display_dramatic_context_items.forEach(function (row) {
        block += "<dt>" + escapeHtml(row.label) + "</dt><dd>" + escapeHtml(row.value) + "</dd>";
      });
      block += "</dl></details>";
    }
    return block;
  }

  function entryHtml(rawEntry) {
    const entry = normalizeEntry(rawEntry);
    const speaker = entry.speaker || "World of Shadows";
    const turn = entry.turn_number != null ? "Turn " + escapeHtml(entry.turn_number) + " · " : "";
    let html = '<article class="play-turn-card play-turn-card--fresh">';
    html += '<header class="play-turn-card__meta">' + turn + escapeHtml(speaker) + "</header>";
    if (entry.role === "player") {
      html += '<p class="runtime-player-line"><strong>You:</strong> ' + escapeHtml(entry.text || "") + "</p>";
    } else if (entry.text) {
      html += '<div class="play-story-output">';
      html +=
        '<div class="play-story-text play-turn-card__narration play-narration--reveal">' +
        escapeHtml(entry.text) +
        "</div>";
      html += "</div>";
    }
    if (entry.spoken_lines.length) {
      html += '<h3 class="play-dialogue-label">Spoken</h3><ul class="runtime-spoken play-dialogue-list">';
      entry.spoken_lines.forEach(function (line) {
        html += "<li>" + escapeHtml(line) + "</li>";
      });
      html += "</ul>";
    }
    if (entry.action_lines.length) {
      html += '<h3 class="play-dialogue-label">Action</h3><ul class="runtime-actions play-dialogue-list">';
      entry.action_lines.forEach(function (line) {
        html += "<li>" + escapeHtml(line) + "</li>";
      });
      html += "</ul>";
    }
    if (entry.committed_consequences.length) {
      html += '<h3 class="play-dialogue-label">Consequences</h3><ul class="runtime-consequences">';
      entry.committed_consequences.forEach(function (line) {
        html += "<li>" + escapeHtml(line) + "</li>";
      });
      html += "</ul>";
    }
    if (entry.role === "runtime" && entry.responder_id) {
      html += '<p class="runtime-meta">Responder <code>' + escapeHtml(entry.responder_id) + "</code></p>";
    }
    if (entry.role === "runtime") {
      const sigs = Array.isArray(entry.degradation_signals) ? entry.degradation_signals : [];
      const sigText = sigs.length ? " · signals: " + escapeHtml(sigs.join(", ")) : "";
      html += '<p class="runtime-meta">Quality <code>' + escapeHtml(entry.quality_class || "unknown") + "</code>" + sigText + "</p>";
      html += runtimeDiagnosticsBlockHtml(entry, showPlayDiagnostics);
    }
    if (entry.role === "runtime" && entry.degraded) {
      const reason = entry.degraded_reasons.length ? ": " + escapeHtml(entry.degraded_reasons.join(", ")) : "";
      html += '<p class="play-turn-warning">Degraded runtime path' + reason + "</p>";
    }
    html += "</article>";
    return html;
  }

  function summarizeRuntimeStatus(entries, fallbackStatus) {
    const base = {
      contract: "play_shell_runtime_status.v1",
      selected_responder_id: "",
      validation_status: "",
      quality_class: "healthy",
      degraded: false,
      degraded_reasons: [],
      degradation_summary: "none",
      latest_display_passivity_line: "",
      latest_display_vitality_line: "",
    };
    const status = Object.assign({}, base, fallbackStatus && typeof fallbackStatus === "object" ? fallbackStatus : {});

    status.selected_responder_id = String(status.selected_responder_id || "").trim();
    status.validation_status = String(status.validation_status || "").trim();
    status.quality_class = String(status.quality_class || "healthy").trim() || "healthy";
    status.degraded = Boolean(status.degraded);
    status.degraded_reasons = Array.isArray(status.degraded_reasons)
      ? status.degraded_reasons.map(normalizeLine).filter(Boolean)
      : [];
    status.degradation_summary = String(status.degradation_summary || "").trim() || "none";
    status.latest_display_passivity_line = String(status.latest_display_passivity_line || "").trim();
    status.latest_display_vitality_line = String(status.latest_display_vitality_line || "").trim();

    const runtimeEntries = (entries || []).filter(function (entry) {
      return normalizeEntry(entry).role === "runtime";
    });
    if (runtimeEntries.length) {
      const latest = normalizeEntry(runtimeEntries[runtimeEntries.length - 1]);
      if (latest.responder_id) status.selected_responder_id = latest.responder_id;
      if (latest.validation_status) status.validation_status = latest.validation_status;
      if (latest.quality_class) status.quality_class = latest.quality_class;
      if (latest.degraded) status.degraded = true;
      if (latest.degraded_reasons.length) status.degraded_reasons = latest.degraded_reasons;
      if (latest.degradation_summary) status.degradation_summary = latest.degradation_summary;
      if (latest.display_passivity_line) status.latest_display_passivity_line = latest.display_passivity_line;
      if (latest.display_vitality_line) status.latest_display_vitality_line = latest.display_vitality_line;
    }
    return status;
  }

  function setElementHidden(el, hidden) {
    if (!el) return;
    if (hidden) {
      el.setAttribute("hidden", "hidden");
    } else {
      el.removeAttribute("hidden");
    }
  }

  function renderRuntimeStatus(status) {
    const s = status || {};
    const responderEl = document.getElementById("runtime-selected-responder");
    if (responderEl) {
      responderEl.innerHTML =
        "Responder: <code>" + escapeHtml(s.selected_responder_id || "n/a") + "</code>";
    }
    const validationEl = document.getElementById("runtime-validation-status");
    if (validationEl) {
      validationEl.innerHTML =
        "Validation: <code>" + escapeHtml(s.validation_status || "unknown") + "</code>";
    }
    const qualityEl = document.getElementById("runtime-quality-class");
    if (qualityEl) {
      qualityEl.innerHTML = "Quality: <code>" + escapeHtml(s.quality_class || "unknown") + "</code>";
    }
    const degSummaryEl = document.getElementById("runtime-degradation-summary");
    if (degSummaryEl) {
      const ds = String(s.degradation_summary || "").trim() || "none";
      degSummaryEl.innerHTML = "Degradation summary: <code>" + escapeHtml(ds) + "</code>";
      setElementHidden(degSummaryEl, !ds || ds === "none");
    }
    const passEl = document.getElementById("runtime-passivity-line");
    if (passEl) {
      const t = String(s.latest_display_passivity_line || "").trim();
      passEl.textContent = t;
      setElementHidden(passEl, !t);
    }
    const vitEl = document.getElementById("runtime-vitality-line");
    if (vitEl) {
      const t = String(s.latest_display_vitality_line || "").trim();
      vitEl.textContent = t;
      setElementHidden(vitEl, !t);
    }
    const bannerEl = document.getElementById("runtime-degraded-banner");
    if (bannerEl) {
      const degraded = Boolean(s.degraded);
      const reasons = Array.isArray(s.degraded_reasons) ? s.degraded_reasons : [];
      const reasonText = reasons.length ? " \u00b7 " + reasons.join(", ") : "";
      bannerEl.textContent = "Degraded runtime path" + reasonText;
      setElementHidden(bannerEl, !degraded);
    }
  }

  function renderEntries(entries, runtimeStatusOverride) {
    const transcriptRoot = document.getElementById("turn-transcript");
    if (!transcriptRoot) return;
    const normalizedEntries = Array.isArray(entries) ? entries.map(normalizeEntry) : [];
    if (!normalizedEntries.length) {
      transcriptRoot.innerHTML = storyPlaceholderHtml();
      renderRuntimeStatus(summarizeRuntimeStatus([], runtimeStatusOverride));
      return;
    }
    transcriptRoot.innerHTML = normalizedEntries.map(entryHtml).join("");
    renderRuntimeStatus(summarizeRuntimeStatus(normalizedEntries, runtimeStatusOverride));
    transcriptRoot.scrollTop = transcriptRoot.scrollHeight;
    const lastCard = transcriptRoot.querySelector(".play-turn-card:last-of-type");
    if (lastCard && typeof lastCard.scrollIntoView === "function") {
      lastCard.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
    window.setTimeout(function () {
      document.querySelectorAll(".play-turn-card--fresh").forEach(function (el) {
        el.classList.remove("play-turn-card--fresh");
      });
    }, 1000);
  }

  function extractEntriesFromPayload(payload) {
    if (Array.isArray(payload)) return payload;
    if (!payload || typeof payload !== "object") return null;
    if (Array.isArray(payload.story_entries)) return payload.story_entries;
    if (payload.story_window && Array.isArray(payload.story_window.entries)) return payload.story_window.entries;
    if (payload.type === "snapshot" && payload.data && payload.data.story_window && Array.isArray(payload.data.story_window.entries)) {
      return payload.data.story_window.entries;
    }
    if (payload.data && Array.isArray(payload.data.story_entries)) return payload.data.story_entries;
    return null;
  }

  function extractRuntimeStatusFromPayload(payload) {
    if (!payload || typeof payload !== "object") return null;
    if (payload.runtime_status_view && typeof payload.runtime_status_view === "object") {
      return payload.runtime_status_view;
    }
    if (payload.data && payload.data.runtime_status_view && typeof payload.data.runtime_status_view === "object") {
      return payload.data.runtime_status_view;
    }
    return null;
  }

  function extractShowDiagnosticsFromPayload(payload) {
    if (!payload || typeof payload !== "object") return null;
    if (typeof payload.show_play_diagnostics === "boolean") return payload.show_play_diagnostics;
    if (payload.data && typeof payload.data.show_play_diagnostics === "boolean") {
      return payload.data.show_play_diagnostics;
    }
    return null;
  }

  function parsePayload(raw) {
    if (raw == null) return null;
    if (typeof raw === "string") {
      try {
        return JSON.parse(raw);
      } catch (_err) {
        return null;
      }
    }
    if (typeof raw === "object") return raw;
    return null;
  }

  function applyShowDiagnosticsFromPayload(payload) {
    const v = extractShowDiagnosticsFromPayload(payload);
    if (typeof v === "boolean") {
      showPlayDiagnostics = v;
      if (shell) {
        shell.setAttribute("data-show-play-diagnostics", v ? "true" : "false");
      }
    }
  }

  function applyRuntimePayload(rawPayload) {
    const payload = parsePayload(rawPayload);
    if (!payload) return false;
    applyShowDiagnosticsFromPayload(payload);
    const entries = extractEntriesFromPayload(payload);
    const runtimeStatus = extractRuntimeStatusFromPayload(payload);
    if (!entries && !runtimeStatus) return false;
    if (entries) {
      renderEntries(entries, runtimeStatus || undefined);
      return true;
    }
    if (runtimeStatus) {
      renderRuntimeStatus(summarizeRuntimeStatus([], runtimeStatus));
      return true;
    }
    return false;
  }

  window.playShellApplyRuntimePayload = applyRuntimePayload;
  window.addEventListener("play-shell-runtime-update", function (event) {
    if (!event) return;
    applyRuntimePayload(event.detail);
  });
  window.addEventListener("message", function (event) {
    if (!event) return;
    applyRuntimePayload(event.data);
  });

  const bootstrapEl = document.getElementById("play-shell-bootstrap");
  if (bootstrapEl) {
    const bootstrapPayload = parsePayload(bootstrapEl.textContent || "{}") || {};
    applyShowDiagnosticsFromPayload(bootstrapPayload);
    if (extractShowDiagnosticsFromPayload(bootstrapPayload) === null && shell) {
      showPlayDiagnostics = shell.getAttribute("data-show-play-diagnostics") === "true";
    }
    const initialEntries = extractEntriesFromPayload(bootstrapPayload) || [];
    const initialStatus = extractRuntimeStatusFromPayload(bootstrapPayload);
    renderRuntimeStatus(summarizeRuntimeStatus(initialEntries, initialStatus || undefined));
  }

  const form = document.getElementById("play-execute-form");
  const executeStatus = document.getElementById("execute-status");
  if (!form) return;

  form.addEventListener("submit", function (ev) {
    const ta = document.getElementById("player-input");
    if (!ta || !ta.value.trim()) return;
    ev.preventDefault();
    const btn = document.getElementById("execute-turn-btn");
    if (btn) btn.disabled = true;
    if (executeStatus) executeStatus.textContent = "Submitting turn...";
    fetch(form.action, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      credentials: "same-origin",
      body: JSON.stringify({ player_input: ta.value.trim() }),
    })
      .then(function (r) {
        return r.json().then(function (data) {
          return { ok: r.ok, data: data };
        });
      })
      .then(function (res) {
        if (!res.ok || !res.data.ok) {
          if (executeStatus) executeStatus.textContent = (res.data && res.data.error) || "Turn failed.";
          return;
        }
        if (typeof res.data.show_play_diagnostics === "boolean") {
          showPlayDiagnostics = res.data.show_play_diagnostics;
          if (shell) {
            shell.setAttribute("data-show-play-diagnostics", showPlayDiagnostics ? "true" : "false");
          }
        }
        renderEntries(res.data.story_entries || [], res.data.runtime_status_view || undefined);
        ta.value = "";
        if (executeStatus) {
          const degraded = Boolean(res.data.runtime_status_view && res.data.runtime_status_view.degraded);
          executeStatus.textContent = degraded
            ? "Story updated (degraded runtime path)."
            : "Story updated.";
        }
      })
      .catch(function () {
        if (executeStatus) executeStatus.textContent = "Network error. Try again.";
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  });

  // Phase D: QA Canonical Turn Diagnostics Panel
  var showQaDiagnostics = false;
  var qaPanel = null;

  function initQaDiagnosticsPanel() {
    // Check if QA diagnostics should be enabled
    const params = new URLSearchParams(window.location.search);
    const qaMode = params.get("diagnostics") === "qa";
    showQaDiagnostics = qaMode;

    if (!showQaDiagnostics) return;

    // Create QA panel container
    qaPanel = document.createElement("div");
    qaPanel.id = "qa-diagnostics-panel";
    qaPanel.setAttribute("class", "qa-diagnostics-panel");
    qaPanel.style.display = "none";
    qaPanel.innerHTML =
      '<div class="qa-diagnostics-header">' +
      '<button class="qa-diagnostics-close">Close</button>' +
      '<h3>QA Canonical Turn Diagnostics</h3>' +
      '</div>' +
      '<div class="qa-diagnostics-content">' +
      '<p class="qa-loading">Loading...</p>' +
      '</div>';

    shell.appendChild(qaPanel);

    // Close button
    const closeBtn = qaPanel.querySelector(".qa-diagnostics-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        qaPanel.style.display = "none";
      });
    }

    // Fetch canonical turn data
    const sessionId = shell.getAttribute("data-session-id");
    if (!sessionId) {
      updateQaPanelContent("Error: Session ID not found.");
      return;
    }

    fetch("/api/v1/play/" + encodeURIComponent(sessionId) + "/qa-diagnostics-canonical-turn?include_raw=0", {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
      credentials: "same-origin",
    })
      .then(function (r) {
        if (r.status === 403) {
          return r.json().then(function (data) {
            updateQaPanelContent("Not authorized for QA diagnostics. Ensure FEATURE_VIEW_QA_CANONICAL_TURN is enabled.");
          });
        }
        if (r.status === 404) {
          return r.json().then(function (data) {
            updateQaPanelContent("Session not found or runtime state unavailable.");
          });
        }
        if (!r.ok) {
          return r.json().then(function (data) {
            updateQaPanelContent("Error: " + (data.error || "Failed to load QA diagnostics."));
          });
        }
        return r.json().then(function (data) {
          if (data.ok) {
            displayQaDiagnostics(data.data);
          } else {
            updateQaPanelContent("Error: " + (data.error || "Invalid response."));
          }
        });
      })
      .catch(function (err) {
        updateQaPanelContent("Network error: " + (err.message || "Could not reach server."));
      });

    qaPanel.style.display = "block";
  }

  function updateQaPanelContent(message) {
    if (!qaPanel) return;
    const content = qaPanel.querySelector(".qa-diagnostics-content");
    if (content) {
      content.innerHTML = "<p>" + escapeHtml(message) + "</p>";
    }
  }

  function displayQaDiagnostics(projection) {
    if (!qaPanel) return;
    const content = qaPanel.querySelector(".qa-diagnostics-content");
    if (!content) return;

    let html = '<div class="qa-diagnostics-view">';

    // Tier A: Primary fields
    const tierA = projection.tier_a_primary || {};
    if (Object.keys(tierA).length > 0) {
      html += '<section class="qa-section qa-section-tier-a">';
      html += '<h4>Primary Information</h4>';
      html += formatQaSection(tierA);
      html += "</section>";
    }

    // Tier B: Detailed fields (collapsed)
    const tierB = projection.tier_b_detailed || {};
    if (Object.keys(tierB).length > 0) {
      html += '<details class="qa-section qa-section-tier-b">';
      html += '<summary>Detailed Information (Tier B)</summary>';
      html += formatQaSection(tierB);
      html += "</details>";
    }

    // Graph execution summary
    const graphSum = projection.graph_execution_summary || {};
    if (Object.keys(graphSum).length > 0) {
      html += '<details class="qa-section qa-section-graph">';
      html += '<summary>Graph Execution (Tier B)</summary>';
      html += formatQaSection(graphSum);
      html += "</details>";
    }

    // Raw JSON toggle
    if (projection.raw_canonical_record_available) {
      html +=
        '<details class="qa-section qa-section-raw">' +
        '<summary>Raw Canonical Record (JSON)</summary>' +
        '<pre class="qa-raw-json"><code>Note: Include ?include_raw=1 in URL to fetch full canonical record.</code></pre>' +
        "</details>";
    }

    html += "</div>";
    content.innerHTML = html;
  }

  function formatQaSection(obj) {
    let html = "<dl>";
    for (const [key, value] of Object.entries(obj)) {
      if (value === null || value === undefined) continue;
      html += "<dt>" + escapeHtml(String(key)) + "</dt>";
      if (typeof value === "object") {
        html +=
          "<dd><pre><code>" +
          escapeHtml(JSON.stringify(value, null, 2)) +
          "</code></pre></dd>";
      } else {
        html += "<dd>" + escapeHtml(String(value)) + "</dd>";
      }
    }
    html += "</dl>";
    return html;
  }

  // Initialize QA panel if diagnostics=qa is present
  initQaDiagnosticsPanel();
})();
