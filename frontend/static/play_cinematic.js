/**
 * Cinematic live-direction wiring (ADR-0046)
 *
 * Owns:
 *   - the "Director composing…" pulse between player-submit and first block;
 *   - player-echo fade on the most recent player turn card while engine
 *     delivers;
 *   - story-window heartbeat / ambient-pulse during active typing;
 *   - skip-button speedrun toggle on the play shell;
 *   - role_anchor opening sweep on first mount.
 *
 * Listens to events dispatched by play_blocks_orchestrator.js:
 *   - play-cinematic-slice-start   { block, beat_changed }
 *   - play-cinematic-idle          {}
 *
 * No knowledge of the engine internals — purely a presentation layer.
 */
(function () {
  "use strict";

  const shell = document.querySelector(".play-shell");
  if (!shell) return;

  const storyWindow = document.getElementById("play-story-window");
  const transcript = document.getElementById("turn-transcript");
  const inputDock = document.getElementById("play-input-dock");
  const form = document.getElementById("play-execute-form");

  /* ── Composing indicator ─────────────────────────────────────────────── */
  let composingEl = null;
  function ensureComposing() {
    if (composingEl) return composingEl;
    composingEl = document.createElement("div");
    composingEl.className = "play-composing";
    composingEl.setAttribute("aria-live", "polite");
    composingEl.innerHTML =
      '<span class="play-composing__label mono">Director composing</span>' +
      '<span class="play-composing__dots" aria-hidden="true">' +
        '<span class="play-composing__dot">◇</span>' +
        '<span class="play-composing__dot">◆</span>' +
        '<span class="play-composing__dot">◇</span>' +
      '</span>';
    return composingEl;
  }
  function showComposing() {
    const el = ensureComposing();
    if (!inputDock) return;
    if (!el.parentNode) inputDock.insertBefore(el, inputDock.firstChild);
    el.classList.add("is-active");
  }
  function hideComposing() {
    if (!composingEl) return;
    composingEl.classList.remove("is-active");
  }

  /* ── Player-echo fade on last player turn card ───────────────────────── */
  let echoingCard = null;
  function applyPlayerEcho() {
    if (!transcript) return;
    const playerCards = transcript.querySelectorAll(".play-turn-card .runtime-player-line");
    if (!playerCards.length) return;
    const last = playerCards[playerCards.length - 1].closest(".play-turn-card");
    if (!last) return;
    last.classList.add("play-turn-card--echoing");
    echoingCard = last;
  }
  function releasePlayerEcho() {
    if (echoingCard) {
      echoingCard.classList.remove("play-turn-card--echoing");
      echoingCard = null;
    }
  }

  /* ── Story-window heartbeat / ambient pulse ──────────────────────────── */
  function setStreaming(on) {
    if (!storyWindow) return;
    storyWindow.classList.toggle("is-stream-active", !!on);
  }
  function setTyping(on) {
    document.body.classList.toggle("is-typing", !!on);
    if (storyWindow) storyWindow.classList.toggle("is-typing", !!on);
  }

  /* ── Skip speedrun ───────────────────────────────────────────────────── */
  const skipBtn = document.getElementById("play-skip-current-btn");
  if (skipBtn) {
    skipBtn.addEventListener("click", function () {
      shell.classList.add("is-speedrun");
      // The orchestrator/engine resolves the skip synchronously; remove the
      // class once the slice settles.
      setTimeout(() => shell.classList.remove("is-speedrun"), 520);
    });
  }

  /* ── Hook form submit for composing + echo ───────────────────────────── */
  if (form) {
    form.addEventListener("submit", function (ev) {
      const ta = document.getElementById("player-input");
      if (!ta || !ta.value.trim()) return;
      // play_shell.js handles the actual fetch; we only paint.
      showComposing();
      applyPlayerEcho();
      setStreaming(true);
    });
  }

  /* ── Orchestrator events ─────────────────────────────────────────────── */
  document.addEventListener("play-cinematic-slice-start", function (event) {
    hideComposing();
    releasePlayerEcho();
    setStreaming(true);
    setTyping(true);
    // role_anchor opening sweep: handled purely in CSS via class match on
    // .scene-block--narrator-role-anchor; nothing to do here.
    const detail = (event && event.detail) || {};
    if (detail.beat_changed && detail.block && detail.block.id) {
      // Optional: future audio hook here.
    }
  });

  document.addEventListener("play-cinematic-idle", function () {
    setTyping(false);
    // Hold streaming-active for one beat so the heartbeat doesn't snap off.
    setTimeout(() => setStreaming(false), 320);
  });

  /* ── Bootstrap on load: if there are story entries already, fire idle  ─
       so initial DOM doesn't get stuck in a streaming state. */
  setTyping(false);
  setStreaming(false);
})();
