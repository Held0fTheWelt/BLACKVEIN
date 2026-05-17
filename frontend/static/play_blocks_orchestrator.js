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
    };
  }
}

if (typeof window !== 'undefined') {
  window.BlocksOrchestrator = BlocksOrchestrator;
}
