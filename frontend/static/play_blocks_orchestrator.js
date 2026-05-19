/**
 * BlocksOrchestrator — State management + event coordination
 *
 * Responsibility: Coordinate BlockRenderer, TypewriterEngine, and PlayControls.
 * Manages blocks array, handles HTTP loads, WebSocket narrator streaming, and user controls.
 *
 * HTTP loadTurn: sliceQueue + currentSliceIndex drive sequential typewriter (ADR-0034 §7).
 * Display text: blockDisplayTextForShell everywhere (shared with renderer).
 */

function _shellDisplayText(block) {
  if (typeof blockDisplayTextForShell === 'function') {
    return String(blockDisplayTextForShell(block) ?? '');
  }
  if (!block) {
    return '';
  }
  return block.player_display_text != null ? String(block.player_display_text) : String(block.text ?? '');
}

class BlocksOrchestrator {
  constructor(renderer, typewriter, controls = null) {
    if (!renderer || !typewriter) {
      throw new Error('BlocksOrchestrator requires renderer and typewriter');
    }

    this.renderer = renderer;
    this.typewriter = typewriter;
    this.controls = controls;

    this.blocks = [];
    this.currentBlockIndex = 0;
    this.accessibility_mode = false;

    /** @type {object[]} Blocks in the animated slice (indices >= typewriter_slice_start_index), non-diagnostics only */
    this.sliceQueue = [];
    /** @type {number} Index into sliceQueue for the block currently being typed */
    this.currentSliceIndex = 0;
    /** @type {object|null} Diagnostics from last loadTurnFromEventStream call */
    this._lastPrimarySelection = null;

    // ── Phase 2 WS session loop diagnostics ─────────────────────────────────
    /** @type {WebSocket|null} */
    this._wsSocket = null;
    this._wsConnected = false;
    this._wsActiveBlockId = null;
    this._wsLastPlayerCutInEvent = null;
    this._wsCutInCount = 0;
    this._wsStreamFallbackReason = null;
    this._wsLiveInterruptionSupported = false;
    this._wsSessionLoopSupported = false;
    this._wsProofLevel = 'unknown';
    this._wsInputQueue = [];
    this._wsOnMessage = null;

    // ── Phase 2 Stage E: autonomous Director tick diagnostics ──────────────
    this._autonomousTickEvaluatedCount = 0;
    this._autonomousTickBlockReceivedCount = 0;
    this._autonomousTickSilenceCount = 0;
    this._autonomousTickCutInInterruptedCount = 0;
    /** @type {Object|null} latest server-sent summary */
    this._lastAutonomousTickSummary = null;
    /** @type {boolean} true while a block_started message was tagged autonomous */
    this._activeBlockIsAutonomous = false;
  }

  _isDiagnosticsBlock(block) {
    const kind = String((block && block.block_type) || '').toLowerCase();
    return kind.startsWith('diagnostic') || kind.startsWith('debug') || kind === 'system_meta';
  }

  _fillBlockElement(el, block) {
    if (!block) {
      el.textContent = '';
      return;
    }
    el.textContent = _shellDisplayText(block);
  }

  /**
   * Ensure a block has a DOM node (render once). Used for deferred slice cards,
   * revealAll, and accessibility — keeps mount vs typewriter delivery ordered.
   *
   * @param {object} block
   * @returns {HTMLElement|null}
   */
  _mountBlockIfNeeded(block) {
    if (!block || !block.id) {
      return null;
    }
    let el = this.renderer.getBlockElement(block.id);
    if (!el) {
      this.renderer.render(block);
      el = this.renderer.getBlockElement(block.id);
    }
    return el;
  }

  _detachSliceDelivery() {
    if (this.typewriter && typeof this.typewriter.setOnDeliveryComplete === 'function') {
      this.typewriter.setOnDeliveryComplete(null);
    }
  }

  _beatOf(block) {
    return String((block && block.narration_beat) || '').trim().toLowerCase() || 'default';
  }

  _decompressionMs(prevBlock, nextBlock) {
    // Only the real TypewriterEngine carries a `config` object. Mocked
    // typewriters (used in tests) lack it — skip the cinematic gap so
    // unit-test expectations on startDelivery's call signature stay clean.
    if (!this.typewriter || !this.typewriter.config) return 0;
    if (this.typewriter.test_mode) return 0;
    const profiles = this.typewriter.config.beat_profiles
      || (typeof window !== 'undefined' && window.TYPEWRITER_BEAT_PROFILES)
      || {};
    const prevProfile = profiles[this._beatOf(prevBlock)] || profiles.default || {};
    const nextProfile = profiles[this._beatOf(nextBlock)] || profiles.default || {};
    let gap = Number(prevProfile.pause_after || 0) + Number(nextProfile.pause_before || 0);
    if (this._beatOf(prevBlock) !== this._beatOf(nextBlock)) {
      gap += 250; // beat-change decompression
    }
    return Math.max(0, gap);
  }

  _emitCinematicEvent(name, detail) {
    if (typeof document === 'undefined' || typeof document.dispatchEvent !== 'function') return;
    try {
      document.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
    } catch (_e) { /* IE11 fallback unnecessary in this project */ }
  }

  _onSliceDeliveryComplete() {
    const prev = this.sliceQueue[this.currentSliceIndex] || null;
    this.currentSliceIndex++;
    if (this.currentSliceIndex < this.sliceQueue.length) {
      const next = this.sliceQueue[this.currentSliceIndex];
      const el = this._mountBlockIfNeeded(next);
      if (el) {
        this._fillBlockElement(el, null);
      }
      const lead_in_ms = this._decompressionMs(prev, next);
      const beatChanged = this._beatOf(prev) !== this._beatOf(next);
      if (beatChanged && el) {
        el.classList.add('scene-block--beat-decompress');
        setTimeout(() => el.classList.remove('scene-block--beat-decompress'), 600);
      }
      if (lead_in_ms > 0) {
        this.typewriter.startDelivery(next, { lead_in_ms });
      } else {
        this.typewriter.startDelivery(next);
      }
      this._emitCinematicEvent('play-cinematic-slice-start', { block: next, beat_changed: beatChanged });
    } else {
      this._detachSliceDelivery();
      this.sliceQueue = [];
      this.currentSliceIndex = 0;
      this._emitCinematicEvent('play-cinematic-idle', {});
    }
    this.currentBlockIndex = this.blocks.length ? this.blocks.length - 1 : 0;
  }

  /**
   * Load initial turn from HTTP response
   *
   * @param {Object} response - HTTP response with visible_scene_output.blocks
   */
  loadTurn(response) {
    if (!response || !response.visible_scene_output) {
      return;
    }

    const vso = response.visible_scene_output;
    const blocks = vso.blocks || [];

    let twStart;
    const rawStart = vso.typewriter_slice_start_index;
    if (typeof rawStart === 'number' && !Number.isNaN(rawStart)) {
      twStart = Math.max(0, Math.min(Math.floor(rawStart), blocks.length));
    } else if (blocks.length > 0) {
      twStart = blocks.length - 1;
    } else {
      twStart = 0;
    }

    this.renderer.clear();
    this.typewriter.reset();
    this.blocks = [];
    this.sliceQueue = [];
    this.currentSliceIndex = 0;

    const sliceQueue = [];
    for (let i = 0; i < blocks.length; i++) {
      if (i >= twStart && !this._isDiagnosticsBlock(blocks[i])) {
        sliceQueue.push(blocks[i]);
      }
    }
    this.sliceQueue = sliceQueue;

    for (let i = 0; i < blocks.length; i++) {
      const block = blocks[i];
      this.blocks.push(block);

      if (this._isDiagnosticsBlock(block)) {
        this.renderer.render(block);
        continue;
      }

      if (this.accessibility_mode) {
        this.renderer.render(block);
        const el = this._mountBlockIfNeeded(block);
        if (el) {
          this._fillBlockElement(el, block);
        }
        continue;
      }

      const stable = i < twStart;
      if (stable) {
        this.renderer.render(block);
        const el = this._mountBlockIfNeeded(block);
        if (el) {
          this._fillBlockElement(el, block);
        }
        continue;
      }

      // Animated slice (i >= twStart), non-diagnostics: mount first card only; rest deferred.
      const idxInSliceQueue = sliceQueue.findIndex((b) => b.id === block.id);
      if (idxInSliceQueue === 0) {
        this.renderer.render(block);
        const el = this._mountBlockIfNeeded(block);
        if (el) {
          this._fillBlockElement(el, null);
        }
      }
    }

    if (!this.accessibility_mode && this.sliceQueue.length > 0) {
      this.currentSliceIndex = 0;
      if (typeof this.typewriter.setOnDeliveryComplete === 'function') {
        this.typewriter.setOnDeliveryComplete(() => this._onSliceDeliveryComplete());
      }
      const first = this.sliceQueue[0];
      this.typewriter.startDelivery(first);
      this._emitCinematicEvent('play-cinematic-slice-start', { block: first, beat_changed: true });
    }

    if (this.accessibility_mode) {
      this.sliceQueue = [];
      this.currentSliceIndex = 0;
    }

    this.currentBlockIndex = this.blocks.length ? this.blocks.length - 1 : 0;
  }

  /**
   * Append narrator block from WebSocket streaming
   *
   * Each chunk is one block; it becomes the active typewriter slice (ADR-0034 §5–§8).
   *
   * @param {Object} block - Scene block from narrator stream
   */
  appendNarratorBlock(block) {
    const display = _shellDisplayText(block);
    if (!block || !block.id || String(display || '').length === 0) {
      return;
    }

    this._detachSliceDelivery();
    this.sliceQueue = [];
    this.currentSliceIndex = 0;

    this.blocks.push(block);
    this.renderer.render(block);

    if (this._isDiagnosticsBlock(block)) {
      this.currentBlockIndex = this.blocks.length;
      return;
    }

    if (!this.accessibility_mode) {
      this.typewriter.revealAll();
      this.typewriter.startDelivery(block);
      this._emitCinematicEvent('play-cinematic-slice-start', { block: block, beat_changed: true });
      this.currentBlockIndex = this.blocks.length - 1;
    } else {
      const el = this.renderer.getBlockElement(block.id);
      if (el) {
        this._fillBlockElement(el, block);
      }
      this.currentBlockIndex = this.blocks.length;
    }
  }

  /**
   * Skip current block — reveal full text, then continue slice queue if any.
   */
  skipCurrentBlock() {
    const tw = this.typewriter.getQueueState ? this.typewriter.getQueueState() : null;
    const activeId = tw && tw.current_block_id ? tw.current_block_id : null;
    if (!activeId) {
      return;
    }
    this.typewriter.skipBlock(activeId);
  }

  /**
   * Reveal all remaining slice blocks and cancel sequential delivery.
   */
  revealAll() {
    const startIdx = this.currentSliceIndex;
    const pending = this.sliceQueue.slice();

    this._detachSliceDelivery();
    this.typewriter.revealAll();

    if (pending.length > 0) {
      for (let k = startIdx; k < pending.length; k++) {
        const b = pending[k];
        const el = this._mountBlockIfNeeded(b);
        if (el) {
          this._fillBlockElement(el, b);
        }
      }
    }

    this.sliceQueue = [];
    this.currentSliceIndex = 0;
  }

  setAccessibilityMode(enabled) {
    this.accessibility_mode = !!enabled;

    if (enabled) {
      this._detachSliceDelivery();
      this.sliceQueue = [];
      this.currentSliceIndex = 0;
      this.typewriter.revealAll();
      for (let block of this.blocks) {
        const el = this._mountBlockIfNeeded(block);
        if (el) {
          this._fillBlockElement(el, block);
        }
      }
    }
  }

  getState() {
    return {
      blocks_count: this.blocks.length,
      current_block_index: this.currentBlockIndex,
      accessibility_mode: this.accessibility_mode,
      typewriter_state: this.typewriter.getQueueState(),
      slice_queue_length: this.sliceQueue.length,
      current_slice_index: this.currentSliceIndex,
      last_primary_selection: this._lastPrimarySelection,
      ws_session_loop_supported: this._wsSessionLoopSupported,
      live_interruption_supported: this._wsLiveInterruptionSupported,
      ws_connected: this._wsConnected,
      active_block_id: this._wsActiveBlockId,
      last_player_cut_in_event: this._wsLastPlayerCutInEvent,
      cut_in_count: this._wsCutInCount,
      stream_fallback_reason: this._wsStreamFallbackReason,
      proof_level: this._wsProofLevel,
      ws_queued_input_count: this._wsInputQueue.length,
      autonomous_tick_evaluated_count: this._autonomousTickEvaluatedCount,
      autonomous_tick_block_received_count: this._autonomousTickBlockReceivedCount,
      autonomous_tick_silence_count: this._autonomousTickSilenceCount,
      autonomous_tick_cut_in_interrupted_count: this._autonomousTickCutInInterruptedCount,
      last_autonomous_tick_summary: this._lastAutonomousTickSummary,
      active_block_is_autonomous: this._activeBlockIsAutonomous,
    };
  }

  // ── Phase 2 Stage B→C: Event Stream Adapter ────────────────────────────────

  /**
   * Convert a single block_stream_event.v1 to the existing block shape.
   *
   * The block_payload already carries the same fields as a bundle block.
   * This shim extracts it and adds Phase 2 trace fields so blocks rendered
   * from the event stream are distinguishable in dev tools.
   *
   * @param {Object} event - A block_stream_event.v1 dict
   * @returns {Object|null} - Block dict for renderer/typewriter, or null if invalid
   */
  _blockFromStreamEvent(event) {
    if (!event || typeof event !== 'object') return null;
    const payload = event.block_payload;
    if (!payload || typeof payload !== 'object') return null;
    return {
      ...payload,
      _stream_event_id: event.event_id || '',
      _tick_id: event.tick_id || '',
      _lane: event.lane || 'visible_scene_output',
    };
  }

  /**
   * Load turn from block_stream_events (Phase 2 event-stream path).
   *
   * Stage C (primary): when WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED is truthy,
   * reads server-provided readiness diagnostics to decide primary vs fallback.
   * Records the selection in _lastPrimarySelection for diagnostics inspection.
   *
   * Stage B (dual-mode): when only WOS_PHASE2_BLOCK_STREAM_ENABLED is truthy,
   * uses event stream if valid, falls back to bundle without readiness check.
   *
   * Default (both flags off): delegates directly to loadTurn() — bundle path.
   *
   * @param {Object} response - HTTP response with visible_scene_output
   */
  loadTurnFromEventStream(response) {
    const stageC = typeof window !== 'undefined' && !!window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED;
    const stageB = typeof window !== 'undefined' && !!window.WOS_PHASE2_BLOCK_STREAM_ENABLED;

    const vso = (response && response.visible_scene_output) || null;
    const diag = (response && response.diagnostics) || null;
    const readiness = (diag && diag.phase2_event_stream_readiness) || null;
    const streamEvents = (vso && Array.isArray(vso.block_stream_events) && vso.block_stream_events) || null;

    const hasValidEvents = !!(streamEvents && streamEvents.some(
      (e) => e && typeof e === 'object' && e.block_payload && typeof e.block_payload === 'object'
    ));

    // ── Stage C: primary selection with server-provided readiness ─────────────
    if (stageC) {
      const canBePrimary = !!(readiness && readiness.can_be_primary_candidate);

      if (canBePrimary && hasValidEvents) {
        const blocks = [];
        for (const event of streamEvents) {
          const block = this._blockFromStreamEvent(event);
          if (block) blocks.push(block);
        }
        if (blocks.length > 0) {
          this._lastPrimarySelection = {
            event_stream_primary_attempted: true,
            event_stream_primary_used: true,
            event_stream_fallback_used: false,
            event_stream_fallback_reason: null,
            parity_status: (readiness && readiness.parity_status) || null,
            bundle_fallback_available: !!(readiness && readiness.bundle_fallback_available),
          };
          const syntheticVso = {
            ...(vso || {}),
            blocks,
            typewriter_slice_start_index: 0,
            _source: 'phase2_primary_event_stream',
          };
          this.loadTurn({ ...response, visible_scene_output: syntheticVso });
          return;
        }
      }

      // Stage C fallback — record reason, load bundle
      const reason = !hasValidEvents ? 'event_stream_invalid_or_missing'
                   : !readiness ? 'readiness_diagnostics_absent'
                   : 'readiness_not_candidate';
      this._lastPrimarySelection = {
        event_stream_primary_attempted: true,
        event_stream_primary_used: false,
        event_stream_fallback_used: true,
        event_stream_fallback_reason: reason,
        parity_status: (readiness && readiness.parity_status) || null,
        bundle_fallback_available: !!(vso && Array.isArray(vso.blocks) && vso.blocks.length > 0),
      };
      this.loadTurn(response);
      return;
    }

    // ── Stage B: dual-mode gate (no readiness check) ──────────────────────────
    if (!stageB) {
      this.loadTurn(response);
      return;
    }

    if (!hasValidEvents) {
      this.loadTurn(response);
      return;
    }

    const blocks = [];
    for (const event of streamEvents) {
      const block = this._blockFromStreamEvent(event);
      if (block) blocks.push(block);
    }
    if (blocks.length === 0) {
      this.loadTurn(response);
      return;
    }

    const syntheticVso = {
      ...(vso || {}),
      blocks,
      typewriter_slice_start_index: 0,
      _source: 'phase2_event_stream',
    };
    this.loadTurn({ ...response, visible_scene_output: syntheticVso });
  }

  // ── Phase 2 WS Session Loop ────────────────────────────────────────────────

  /**
   * Whether the WS session loop is enabled in this browser window.
   *
   * Server reports support separately; both must be truthy for live cut-in.
   * @returns {boolean}
   */
  isWsSessionLoopFlagEnabled() {
    return (typeof window !== 'undefined' && !!window.WOS_PHASE2_WS_SESSION_LOOP_ENABLED);
  }

  /**
   * Connect to the Phase 2 story-session WebSocket.
   *
   * Falls back silently to REST/bundle if the flag is off, the WebSocket
   * global is missing, or the socket fails to open. Never throws.
   *
   * @param {Object} opts
   * @param {string} opts.url               — ws:// or wss:// URL (no key)
   * @param {string} [opts.key]             — internal API key (query param ?key=)
   * @param {Function} [opts.onFallback]    — invoked with (reason) when WS unusable
   * @param {Function} [opts.restFallback]  — invoked when WS fails post-connect
   * @returns {boolean} — true when a connection attempt was started
   */
  connectStream(opts) {
    const options = opts || {};
    if (!this.isWsSessionLoopFlagEnabled()) {
      this._wsStreamFallbackReason = 'flag_disabled';
      if (typeof options.onFallback === 'function') options.onFallback('flag_disabled');
      return false;
    }
    if (typeof WebSocket === 'undefined') {
      this._wsStreamFallbackReason = 'websocket_unavailable';
      if (typeof options.onFallback === 'function') options.onFallback('websocket_unavailable');
      return false;
    }
    let url = String(options.url || '');
    if (!url) {
      this._wsStreamFallbackReason = 'missing_url';
      if (typeof options.onFallback === 'function') options.onFallback('missing_url');
      return false;
    }
    if (options.key) {
      const sep = url.indexOf('?') >= 0 ? '&' : '?';
      url = url + sep + 'key=' + encodeURIComponent(String(options.key));
    }

    let socket;
    try {
      socket = new WebSocket(url);
    } catch (err) {
      this._wsStreamFallbackReason = 'connect_threw';
      if (typeof options.onFallback === 'function') options.onFallback('connect_threw');
      return false;
    }
    this._wsSocket = socket;
    this._wsSessionLoopSupported = true; // tentative; server stream_started confirms

    socket.onopen = () => {
      this._wsConnected = true;
      this._wsStreamFallbackReason = null;
    };
    socket.onclose = () => {
      this._wsConnected = false;
      this._wsActiveBlockId = null;
      this._wsLiveInterruptionSupported = false;
      this._wsSocket = null;
    };
    socket.onerror = () => {
      this._wsConnected = false;
      this._wsStreamFallbackReason = this._wsStreamFallbackReason || 'socket_error';
      if (typeof options.restFallback === 'function') options.restFallback('socket_error');
    };
    socket.onmessage = (ev) => {
      let parsed;
      try { parsed = JSON.parse(ev.data); }
      catch (_e) { return; }
      this._handleWsMessage(parsed);
      if (typeof this._wsOnMessage === 'function') {
        try { this._wsOnMessage(parsed); } catch (_e) { /* ignore */ }
      }
    };
    return true;
  }

  /**
   * Send a start_turn request over WS. Returns true if dispatched.
   *
   * @param {string} playerInput
   */
  wsStartTurn(playerInput) {
    if (!this._wsSocket || this._wsSocket.readyState !== 1 /* OPEN */) return false;
    const text = String(playerInput || '').trim();
    if (!text) return false;
    this._wsSocket.send(JSON.stringify({ kind: 'start_turn', player_input: text }));
    return true;
  }

  /**
   * Send a cut_in over WS while a block is streaming.
   *
   * Never loses the input: if the socket isn't open, it is queued in
   * ``_wsInputQueue`` so the caller can replay it on the next turn (e.g.
   * via the REST path or a reconnected WS).
   *
   * @param {string} playerInput
   * @returns {boolean}
   */
  sendCutIn(playerInput) {
    const text = String(playerInput || '').trim();
    if (!text) return false;
    if (!this._wsSocket || this._wsSocket.readyState !== 1 /* OPEN */) {
      this._wsInputQueue.push({ player_input: text, queued_at: Date.now(), reason: 'ws_not_open' });
      return false;
    }
    this._wsSocket.send(JSON.stringify({ kind: 'cut_in', player_input: text }));
    return true;
  }

  /**
   * Disconnect the WS session loop. Safe to call multiple times.
   */
  disconnectStream() {
    if (this._wsSocket && typeof this._wsSocket.close === 'function') {
      try { this._wsSocket.close(); } catch (_e) { /* ignore */ }
    }
    this._wsSocket = null;
    this._wsConnected = false;
    this._wsActiveBlockId = null;
    this._wsLiveInterruptionSupported = false;
  }

  /**
   * Drain queued player inputs (e.g. for replay over REST after WS failure).
   * @returns {Object[]}
   */
  drainQueuedPlayerInputs() {
    const drained = this._wsInputQueue.slice();
    this._wsInputQueue = [];
    return drained;
  }

  /**
   * Handle a server → client WS message. Internal — exposed for tests via
   * direct invocation (no behavior changes if called manually).
   *
   * @param {Object} message
   */
  _handleWsMessage(message) {
    if (!message || typeof message !== 'object') return;
    const kind = String(message.kind || '');
    if (kind === 'stream_started') {
      this._wsSessionLoopSupported = true;
      this._wsStreamFallbackReason = null;
      this._wsActiveBlockId = null;
      this._wsLiveInterruptionSupported = false;
      this._wsProofLevel = 'live_loop_active';
      return;
    }
    if (kind === 'autonomous_tick_evaluated') {
      this._autonomousTickEvaluatedCount = (this._autonomousTickEvaluatedCount || 0) + 1;
      const summary = (message.summary && typeof message.summary === 'object') ? message.summary : {};
      this._lastAutonomousTickSummary = summary;
      if (!summary.block_emitted) {
        this._autonomousTickSilenceCount = (this._autonomousTickSilenceCount || 0) + 1;
      }
      return;
    }
    if (kind === 'block_started') {
      const event = message.block_stream_event || null;
      const block = this._blockFromStreamEvent(event);
      this._wsActiveBlockId = message.event_id || (event && event.event_id) || null;
      this._wsLiveInterruptionSupported = !!this._wsActiveBlockId;
      const isAutonomous = !!(
        block && (
          block.originator === 'autonomous_tick'
          || (this._lastAutonomousTickSummary
              && this._lastAutonomousTickSummary.block_emitted
              && this._lastAutonomousTickSummary.tick_id
              && event && event.tick_id === this._lastAutonomousTickSummary.tick_id)
        )
      );
      this._activeBlockIsAutonomous = isAutonomous;
      if (isAutonomous) {
        this._autonomousTickBlockReceivedCount = (this._autonomousTickBlockReceivedCount || 0) + 1;
      }
      if (block) {
        this.appendNarratorBlock(block);
      }
      return;
    }
    if (kind === 'block_completed') {
      this._wsActiveBlockId = null;
      this._wsLiveInterruptionSupported = false;
      this._activeBlockIsAutonomous = false;
      return;
    }
    if (kind === 'block_cut') {
      this._wsCutInCount = (this._wsCutInCount || 0) + 1;
      this._wsLastPlayerCutInEvent = message.player_cut_in_event || null;
      const cutKind = String(message.cut_kind || '');
      if (this._activeBlockIsAutonomous) {
        this._autonomousTickCutInInterruptedCount = (this._autonomousTickCutInInterruptedCount || 0) + 1;
      }
      if (cutKind === 'em_dash') {
        this._applyEmDashToActiveBlock();
      } else if (cutKind === 'skip_to_end') {
        try { this.revealAll(); } catch (_e) { /* ignore */ }
      }
      this._wsActiveBlockId = null;
      this._wsLiveInterruptionSupported = false;
      this._activeBlockIsAutonomous = false;
      return;
    }
    if (kind === 'stream_idle') {
      this._wsActiveBlockId = null;
      this._wsLiveInterruptionSupported = false;
      this._activeBlockIsAutonomous = false;
      return;
    }
    if (kind === 'stream_error') {
      this._wsStreamFallbackReason = String(message.reason || 'stream_error');
      this._wsLiveInterruptionSupported = false;
      return;
    }
  }

  /**
   * Append "—" to the currently active block as a visual em-dash cut marker.
   * No-ops in accessibility mode (em-dash is purely a typewriter affordance).
   */
  _applyEmDashToActiveBlock() {
    if (this.accessibility_mode) return;
    const tw = this.typewriter.getQueueState ? this.typewriter.getQueueState() : null;
    const activeId = tw && tw.current_block_id ? tw.current_block_id : (this._wsActiveBlockId || null);
    if (!activeId) return;
    const el = this.renderer.getBlockElement(activeId);
    if (!el) return;
    const current = String(el.textContent || '');
    if (current.endsWith('—')) return;
    el.textContent = current.replace(/\s+$/, '') + '—';
    if (typeof this.typewriter.skipBlock === 'function') {
      try { this.typewriter.skipBlock(activeId); } catch (_e) { /* ignore */ }
    }
  }
}

if (typeof window !== 'undefined') {
  window.BlocksOrchestrator = BlocksOrchestrator;
}
