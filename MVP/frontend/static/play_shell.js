(function () {
  const connectBtn = document.getElementById("connect-btn");
  const status = document.getElementById("socket-status");
  const wsBaseEl = document.getElementById("ws-base");
  const ticketEl = document.getElementById("play-ticket");
  if (!connectBtn || !status || !wsBaseEl || !ticketEl) return;

  let socket = null;
  connectBtn.addEventListener("click", function () {
    const wsBase = (wsBaseEl.textContent || "").trim().replace(/\/$/, "");
    const ticket = (ticketEl.textContent || "").trim();
    if (!wsBase || !ticket) {
      status.textContent = "Missing WebSocket ticket data";
      return;
    }
    if (socket) {
      socket.close();
    }
    const url = `${wsBase}/ws?ticket=${encodeURIComponent(ticket)}`;
    socket = new WebSocket(url);
    status.textContent = "Connecting...";
    socket.onopen = function () {
      status.textContent = "Connected";
    };
    socket.onclose = function () {
      status.textContent = "Disconnected";
    };
    socket.onerror = function () {
      status.textContent = "Socket error";
    };
    socket.onmessage = function (event) {
      status.textContent = `Live update received (${event.data.length} bytes)`;
    };
  });
})();

(function () {
  const form = document.getElementById("execute-form");
  if (!form) return;

  const statusBox = document.getElementById("shell-execute-status");
  const runTitle = document.getElementById("run-title");
  const templateSource = document.getElementById("template-source");
  const lobbyStatus = document.getElementById("lobby-status");
  const transcriptCount = document.getElementById("observed-transcript-count");
  const authoritativeStatusSummary = document.getElementById("authoritative-status-summary");
  const observationSource = document.getElementById("observation-source");
  const observationError = document.getElementById("observation-error");
  const observationSourceBadge = document.getElementById("observation-source-badge");
  const runtimeSessionReady = document.getElementById("runtime-session-ready");
  const runtimeSessionId = document.getElementById("runtime-session-id");
  const runtimeRecoveryStatus = document.getElementById("runtime-recovery-status");
  const runtimeRecoveryMessage = document.getElementById("runtime-recovery-message");
  const runtimeRecoveryError = document.getElementById("runtime-recovery-error");
  const executeBtn = document.getElementById("execute-turn-btn");
  const observedRunStatus = document.getElementById("observed-run-status");
  const latestLine = document.getElementById("latest-transcript-line");
  const latestLineWrapper = document.getElementById("latest-transcript-line-wrapper");
  const transcriptList = document.getElementById("transcript-preview-list");
  const transcriptEmpty = document.getElementById("transcript-preview-empty");
  const input = document.getElementById("player-input");
  const refreshBtn = document.getElementById("refresh-observation-btn");
  const socialWeatherNow = document.getElementById("social-weather-now");
  const liveSurfaceNow = document.getElementById("live-surface-now");
  const carryoverNow = document.getElementById("carryover-now");
  const socialGeometryNow = document.getElementById("social-geometry-now");
  const situationalFreedomNow = document.getElementById("situational-freedom-now");
  const addressPressureNow = document.getElementById("address-pressure-now");
  const socialMomentNow = document.getElementById("social-moment-now");
  const responsePressureNow = document.getElementById("response-pressure-now");
  const whoAnswersNow = document.getElementById("who-answers-now");
  const whyThisReplyNow = document.getElementById("why-this-reply-now");
  const observationFootholdNow = document.getElementById("observation-foothold-now");
  const reactionDeltaNow = document.getElementById("reaction-delta-now");
  const carryoverDeltaNow = document.getElementById("carryover-delta-now");
  const pressureShiftDeltaNow = document.getElementById("pressure-shift-delta-now");
  const hotSurfaceDeltaNow = document.getElementById("hot-surface-delta-now");

  function setStatus(text, level) {
    if (!statusBox) return;
    statusBox.textContent = text || "";
    statusBox.dataset.level = level || "info";
  }

  function renderTranscriptPreview(lines) {
    if (!transcriptList || !transcriptEmpty) return;
    transcriptList.innerHTML = "";
    if (Array.isArray(lines) && lines.length) {
      lines.forEach(function (line) {
        const li = document.createElement("li");
        li.textContent = line;
        transcriptList.appendChild(li);
      });
      transcriptList.hidden = false;
      transcriptEmpty.hidden = true;
    } else {
      transcriptList.hidden = true;
      transcriptEmpty.hidden = false;
    }
  }

  function applyShellStateBundle(data) {
    const shell = (data && data.shell_state_view) || {};
    if (observationSource) observationSource.textContent = (data && data.observation_source) || "unknown";
    if (observationError) observationError.textContent = (data && data.observation_error) ? `(${data.observation_error})` : "";
    if (observationSourceBadge) {
      const meta = (data && data.observation_meta) || {};
      observationSourceBadge.textContent = meta.is_fresh ? "fresh" : (meta.is_cached_fallback ? "cached fallback" : (meta.is_unavailable ? "unavailable" : "observed"));
    }
    if (runtimeSessionReady) runtimeSessionReady.textContent = data && data.runtime_session_ready ? "yes" : "no";
    if (runtimeSessionId) runtimeSessionId.textContent = (data && data.backend_session_id) || "not ready";
    if (runtimeRecoveryStatus) runtimeRecoveryStatus.textContent = (data && data.runtime_recovery_status) || (((data || {}).runtime_recovery || {}).status) || "not_ready";
    if (runtimeRecoveryMessage) runtimeRecoveryMessage.textContent = (data && data.runtime_recovery_message) || (((data || {}).runtime_recovery || {}).message) || "";
    if (runtimeRecoveryError) {
      const recoveryErrorText = (data && data.runtime_recovery_error) || (((data || {}).runtime_recovery || {}).error) || "";
      runtimeRecoveryError.textContent = recoveryErrorText ? `(${recoveryErrorText})` : "";
    }
    if (executeBtn) executeBtn.disabled = !(data && data.can_execute);
    if (runTitle) runTitle.textContent = shell.run_title || runTitle.textContent;
    if (templateSource) templateSource.textContent = shell.template_source || templateSource.textContent;
    if (lobbyStatus) lobbyStatus.textContent = shell.lobby_status || lobbyStatus.textContent;
    if (transcriptCount) transcriptCount.textContent = String(shell.transcript_entry_count || 0);
    if (authoritativeStatusSummary) authoritativeStatusSummary.textContent = shell.authoritative_status_summary || "";
    if (observedRunStatus) observedRunStatus.textContent = shell.run_status || observedRunStatus.textContent || "";
    if (socialWeatherNow) socialWeatherNow.textContent = shell.social_weather_now || "";
    if (liveSurfaceNow) liveSurfaceNow.textContent = shell.live_surface_now || "";
    if (carryoverNow) carryoverNow.textContent = shell.carryover_now || "";
    if (socialGeometryNow) socialGeometryNow.textContent = shell.social_geometry_now || "";
    if (situationalFreedomNow) situationalFreedomNow.textContent = shell.situational_freedom_now || "";
    if (addressPressureNow) addressPressureNow.textContent = shell.address_pressure_now || "";
    if (socialMomentNow) socialMomentNow.textContent = shell.social_moment_now || "";
    if (responsePressureNow) responsePressureNow.textContent = shell.response_pressure_now || "";
    if (whoAnswersNow) whoAnswersNow.textContent = shell.who_answers_now || "";
    if (whyThisReplyNow) whyThisReplyNow.textContent = shell.why_this_reply_now || "";
    if (observationFootholdNow) observationFootholdNow.textContent = shell.observation_foothold_now || "";
    if (reactionDeltaNow) reactionDeltaNow.textContent = shell.reaction_delta_now || "";
    if (carryoverDeltaNow) carryoverDeltaNow.textContent = shell.carryover_delta_now || "";
    if (pressureShiftDeltaNow) pressureShiftDeltaNow.textContent = shell.pressure_shift_delta_now || "";
    if (hotSurfaceDeltaNow) hotSurfaceDeltaNow.textContent = shell.hot_surface_delta_now || "";
    if (latestLine && latestLineWrapper) {
      if (shell.latest_entry_text) {
        latestLine.textContent = shell.latest_entry_text;
        latestLineWrapper.hidden = false;
      } else {
        latestLine.textContent = "";
        latestLineWrapper.hidden = true;
      }
    }
    renderTranscriptPreview(shell.transcript_preview || []);
  }

  async function fetchAuthoritativeObservation() {
    if (!refreshBtn || !refreshBtn.dataset.observeUrl) return null;
    const response = await fetch(refreshBtn.dataset.observeUrl, {
      method: "GET",
      credentials: "same-origin",
      headers: {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Authoritative refresh failed.");
    }
    return data;
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = { player_input: (formData.get("player_input") || "").toString() };
    setStatus("Executing turn and refreshing authoritative view...", "info");
    try {
      const response = await fetch(form.action, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        setStatus(data.error || "Turn execution failed.", "error");
        return;
      }
      applyShellStateBundle(data);
      if (input) input.value = "";
      setStatus(data.message || "Turn executed.", data.authoritative_refresh_error ? "warning" : "success");
    } catch (err) {
      setStatus("Turn execution failed before authoritative refresh completed.", "error");
    }
  });

  const initialStateNode = document.getElementById("initial-shell-state");
  if (initialStateNode && initialStateNode.textContent) {
    try {
      const initialData = JSON.parse(initialStateNode.textContent);
      applyShellStateBundle(initialData);
    } catch (_err) {
      // ignore malformed hydration payload
    }
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", async function () {
      setStatus("Refreshing authoritative observation...", "info");
      try {
        const data = await fetchAuthoritativeObservation();
        if (data) {
          applyShellStateBundle(data);
          setStatus("Authoritative observation refreshed.", "success");
        }
      } catch (err) {
        setStatus(err.message || "Authoritative refresh failed.", "error");
      }
    });
  }
})();
