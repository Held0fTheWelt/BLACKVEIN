(function () {
  console.log("[PLAY_SHELL] Script loaded and executing");
  const shell = document.querySelector(".play-shell");
  if (!shell) {
    console.warn("[PLAY_SHELL] No .play-shell element found");
    return;
  }
  console.log("[PLAY_SHELL] Shell element found, initializing...");

  var orchestrator = null;
  var typewriterEngine = null;
  var blockRenderer = null;
  var playControls = null;

  function initializeMVP5() {
    const transcriptRoot = document.getElementById("turn-transcript");
    if (!transcriptRoot) {
      console.warn("[MVP5] Could not find turn-transcript element");
      return false;
    }

    // Initialize MVP5 modules (BlockRenderer, BlocksOrchestrator, TypewriterEngine, PlayControls)
    if (typeof window.BlockRenderer === "undefined" || typeof window.BlocksOrchestrator === "undefined" ||
        typeof window.TypewriterEngine === "undefined" || typeof window.PlayControls === "undefined") {
      console.warn("[MVP5] One or more MVP5 modules are not loaded. Falling back to legacy rendering.");
      return false;
    }

    blockRenderer = new window.BlockRenderer(transcriptRoot);
    typewriterEngine = new window.TypewriterEngine(window.TEST_MODE || false);
    orchestrator = new window.BlocksOrchestrator(blockRenderer, typewriterEngine);
    playControls = new window.PlayControls(orchestrator);
    playControls.attachEventListeners();

    console.info("[MVP5] Initialized: BlockRenderer, BlocksOrchestrator, TypewriterEngine, PlayControls");
    return true;
  }

  var mvp5Ready = false;

  function extractBlocksFromPayload(payload) {
    if (!payload || typeof payload !== "object") return null;
    if (payload.visible_scene_output && Array.isArray(payload.visible_scene_output.blocks)) {
      return payload.visible_scene_output.blocks;
    }
    if (payload.data && payload.data.visible_scene_output && Array.isArray(payload.data.visible_scene_output.blocks)) {
      return payload.data.visible_scene_output.blocks;
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

  function payloadWithRuntimeBoot(payload, options) {
    if (!options || !options.dos_boot) return payload;
    const bootstrap = window.PlayRuntimeBootstrap;
    if (!bootstrap || typeof bootstrap.withDosBootPayload !== "function") {
      return payload;
    }
    return bootstrap.withDosBootPayload(payload);
  }

  function shouldUseRuntimeBoot(payload) {
    const bootstrap = window.PlayRuntimeBootstrap;
    if (!bootstrap || typeof bootstrap.shouldUseDosBoot !== "function") {
      return true;
    }
    return bootstrap.shouldUseDosBoot(payload);
  }

  function applyRuntimePayload(rawPayload, options) {
    const payload = parsePayload(rawPayload);
    if (!payload) return false;

    const displayPayload = payloadWithRuntimeBoot(payload, options || {});
    const blocks = extractBlocksFromPayload(displayPayload);

    if (!blocks) return false;

    if (!mvp5Ready) {
      mvp5Ready = initializeMVP5();
    }
    if (mvp5Ready && orchestrator) {
      orchestrator.loadTurn(displayPayload);
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
    const bootstrapOptions = { dos_boot: shouldUseRuntimeBoot(bootstrapPayload) };
    const applied = applyRuntimePayload(bootstrapPayload, bootstrapOptions);
    const displayPayload = payloadWithRuntimeBoot(bootstrapPayload, bootstrapOptions);
    const blocks = extractBlocksFromPayload(displayPayload);
    if (!applied && blocks && blocks.length) {
      if (!mvp5Ready) {
        mvp5Ready = initializeMVP5();
      }
      if (mvp5Ready && orchestrator) {
        orchestrator.loadTurn(displayPayload);
      }
    }
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
        applyRuntimePayload(res.data);
        ta.value = "";
        if (executeStatus) {
          executeStatus.textContent = "Story updated.";
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
