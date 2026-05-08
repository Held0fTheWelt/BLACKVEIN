/**
 * Phase 5: Narrator Streaming Integration for MVP3
 *
 * Integrates with play_shell.js bootstrap JSON and turn execution to handle:
 * - Real-time narrator block streaming via Server-Sent Events
 * - Typewriter effect rendering
 * - Input-UI blocking during narrative streaming
 * - Automatic streaming initiation after turn execution
 */

(function () {
  const shell = document.querySelector(".play-shell");
  if (!shell) return;

  // Configuration
  const NARRATIVE_STREAM_CONFIG = {
    endpoint_path: "/api/story/sessions/{session_id}/stream-narrator",
    typewriter_speed_ms: 25,  // ms per character
  };

  // State
  let streamState = {
    streaming: false,
    currentSession: null,
    eventSource: null,
    blocks: [],
    ruhepunkt_reached: false,
    reducedMotion: checkReducedMotion(),
  };

  function checkReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function escapeHtml(value) {
    const d = document.createElement("div");
    d.textContent = value == null ? "" : String(value);
    return d.innerHTML;
  }

  function getNarratorBlockHtml(block) {
    if (!block || !block.data) return "";

    const narratorData = block.data.narrator_block || {};
    const blockId = block.event_id || "narrator-" + Math.random().toString(36).substr(2, 9);
    const text = narratorData.narrator_text || narratorData.text || "";
    const tone = narratorData.atmospheric_tone || "";

    if (!text) return "";

    const toneLabel = tone ? ` (${escapeHtml(tone)})` : "";
    let html = `<article class="play-turn-card play-turn-card--narrator" data-block-id="${escapeHtml(blockId)}">`;
    html += `<header class="play-turn-card__meta">Narrator${toneLabel}</header>`;
    html += `<div class="play-story-output">`;
    html += `<div class="play-story-text play-narrator-text" data-typewriter-target="true"></div>`;
    html += `</div></article>`;

    return html;
  }

  function initTypewriter(element, text) {
    if (streamState.reducedMotion) {
      element.textContent = text;
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      let index = 0;
      element.textContent = "";

      function typeNext() {
        if (index < text.length) {
          element.textContent += text.charAt(index);
          index++;
          setTimeout(typeNext, NARRATIVE_STREAM_CONFIG.typewriter_speed_ms);
        } else {
          resolve();
        }
      }

      typeNext();
    });
  }

  function disablePlayerInput(disable) {
    const inputField = document.getElementById("player-input");
    const submitButton = document.getElementById("execute-turn-btn");

    if (inputField) inputField.disabled = disable;
    if (submitButton) submitButton.disabled = disable;

    if (disable) {
      const indicator = document.querySelector(".play-narrator-indicator");
      if (!indicator) {
        // Create indicator if it doesn't exist
        const newIndicator = document.createElement("div");
        newIndicator.className = "play-narrator-indicator";
        newIndicator.textContent = "Narrator is speaking...";
        newIndicator.style.marginTop = "0.5rem";
        newIndicator.style.padding = "0.5rem";
        newIndicator.style.backgroundColor = "#f0f0f0";
        newIndicator.style.borderRadius = "4px";
        newIndicator.style.fontSize = "0.9rem";
        newIndicator.style.color = "#666";
        if (submitButton && submitButton.parentElement) {
          submitButton.parentElement.insertBefore(newIndicator, submitButton.nextSibling);
        }
      } else {
        indicator.hidden = false;
      }
    } else {
      const indicator = document.querySelector(".play-narrator-indicator");
      if (indicator) indicator.hidden = true;
    }
  }

  function handleNarratorEvent(event) {
    if (!event.data) return;

    try {
      const payload = JSON.parse(event.data);

      if (payload.error) {
        console.error("Narrator streaming error:", payload.error, payload.message);
        closeStream();
        return;
      }

      const eventKind = payload.event_kind;

      if (eventKind === "narrator_block") {
        handleNarratorBlock(payload);
      } else if (eventKind === "ruhepunkt_reached") {
        handleRuhepunkt(payload);
      } else if (eventKind === "streaming_complete") {
        handleStreamingComplete(payload);
      } else if (eventKind === "trace_scaffold_emitted" || eventKind === "trace_scaffold_summary") {
        // Phase 6: Trace scaffold events are for observability (diagnostics only)
        // Frontend silently ignores these as they don't affect narrative rendering
        console.debug(`Trace scaffold event received: ${eventKind}`);
      }
    } catch (err) {
      console.error("Failed to parse narrator event:", err);
    }
  }

  function handleNarratorBlock(event) {
    streamState.blocks.push(event);

    // MVP5: Emit narrator-block-received event for BlocksOrchestrator
    if (event.data && event.data.narrator_block) {
      const narratorData = event.data.narrator_block;
      const blockId = event.event_id || "narrator-" + Math.random().toString(36).substr(2, 9);
      const text = narratorData.narrator_text || narratorData.text || "";

      if (text) {
        // Construct block compatible with BlocksOrchestrator
        const block = {
          id: blockId,
          block_type: "narrator",
          text: text,
          speaker_label: "Narrator",
          delivery: {
            mode: "typewriter",
            characters_per_second: 44,
          },
        };

        // Emit custom event for BlocksOrchestrator to consume
        const customEvent = new CustomEvent("narrator-block-received", {
          detail: { block: block },
        });
        window.dispatchEvent(customEvent);
      }
    }

    // Legacy: Also render directly (for compatibility with existing players without BlocksOrchestrator)
    const narratorHtml = getNarratorBlockHtml(event);
    if (!narratorHtml) return;

    const storyOutput = document.getElementById("turn-transcript");
    if (!storyOutput) return;

    const blockElement = document.createElement("div");
    blockElement.innerHTML = narratorHtml;
    storyOutput.appendChild(blockElement);

    const textElement = blockElement.querySelector("[data-typewriter-target]");
    if (textElement && event.data && event.data.narrator_block) {
      const text = event.data.narrator_block.narrator_text || event.data.narrator_block.text || "";
      initTypewriter(textElement, text).catch((err) => {
        console.error("Typewriter animation failed:", err);
      });
    }

    // Auto-scroll to narrator block
    blockElement.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function handleRuhepunkt(event) {
    streamState.ruhepunkt_reached = true;
    disablePlayerInput(false);

    const ruhepunkt = document.querySelector(".play-ruhepunkt-signal");
    if (ruhepunkt) {
      ruhepunkt.hidden = false;
      setTimeout(() => {
        ruhepunkt.hidden = true;
      }, 3000);
    }
  }

  function handleStreamingComplete(event) {
    closeStream();
  }

  function startStreaming(sessionId) {
    if (streamState.streaming) return;

    streamState.streaming = true;
    streamState.currentSession = sessionId;
    streamState.ruhepunkt_reached = false;
    streamState.blocks = [];

    disablePlayerInput(true);

    const endpointUrl = NARRATIVE_STREAM_CONFIG.endpoint_path.replace("{session_id}", sessionId);

    streamState.eventSource = new EventSource(endpointUrl);
    streamState.eventSource.onmessage = handleNarratorEvent;
    streamState.eventSource.onerror = function () {
      console.error("EventSource connection error");
      closeStream();
    };
  }

  function closeStream() {
    if (streamState.eventSource) {
      streamState.eventSource.close();
      streamState.eventSource = null;
    }

    streamState.streaming = false;
    disablePlayerInput(false);
  }

  // Public API
  window.NarrativeStreamer = {
    startStreaming: startStreaming,
    closeStream: closeStream,
    getState: () => Object.assign({}, streamState),
  };

  // Integration with play_shell.js turn execution
  function detectNarratorStreamingFromResponse(responseData) {
    // Called after turn execution to check if narrator streaming should start
    if (responseData && responseData.narrator_streaming) {
      const streaming = responseData.narrator_streaming;
      if (streaming.status === "streaming" && streaming.session_id) {
        setTimeout(() => {
          startStreaming(streaming.session_id);
        }, 100);
        return true;
      }
    }
    return false;
  }

  // Hook into play_shell.js turn execution
  // Intercept the fetch response and check for narrator_streaming
  const originalFetch = window.fetch;
  window.fetch = function (...args) {
    return originalFetch.apply(window, args).then((response) => {
      // Clone response for inspection
      if (response.ok && args[1] && args[1].headers && args[1].headers["Accept"] === "application/json") {
        return response.clone().json().then((data) => {
          // Check for narrator streaming trigger
          if (data && data.ok) {
            detectNarratorStreamingFromResponse(data);
          }
          // Return original response
          return response;
        });
      }
      return response;
    });
  };

  // Also check on initial page load from bootstrap
  const bootstrapEl = document.getElementById("play-shell-bootstrap");
  if (bootstrapEl) {
    try {
      const bootstrapData = JSON.parse(bootstrapEl.textContent || "{}");
      if (bootstrapData && bootstrapData.narrator_streaming) {
        const streaming = bootstrapData.narrator_streaming;
        if (streaming.status === "streaming" && streaming.session_id) {
          // Wait for DOM to be fully ready
          if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", () => {
              setTimeout(() => {
                startStreaming(streaming.session_id);
              }, 100);
            });
          } else {
            setTimeout(() => {
              startStreaming(streaming.session_id);
            }, 100);
          }
        }
      }
    } catch (err) {
      console.error("Failed to parse bootstrap data:", err);
    }
  }
})();
