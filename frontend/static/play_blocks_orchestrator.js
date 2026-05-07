/**
 * BlocksOrchestrator — State management + event coordination
 *
 * Responsibility: Coordinate BlockRenderer, TypewriterEngine, and PlayControls.
 * Manages blocks array, handles HTTP loads, WebSocket narrator streaming, and user controls.
 */

class BlocksOrchestrator {
  constructor(renderer, typewriter, controls = null) {
    if (!renderer || !typewriter) {
      throw new Error('BlocksOrchestrator requires renderer and typewriter');
    }

    this.renderer = renderer;
    this.typewriter = typewriter;
    this.controls = controls;

    this.blocks = []; // All blocks ever rendered
    this.currentBlockIndex = 0; // Which block is being typed
    this.accessibility_mode = false;
  }

  _isDiagnosticsBlock(block) {
    const kind = String((block && block.block_type) || '').toLowerCase();
    return kind.startsWith('diagnostic') || kind.startsWith('debug') || kind === 'system_meta';
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

    /** @type {number} Index into blocks where sequential typewriter begins (ADR-0034 §7). */
    let twStart;
    const rawStart = vso.typewriter_slice_start_index;
    if (typeof rawStart === 'number' && !Number.isNaN(rawStart)) {
      twStart = Math.max(0, Math.min(Math.floor(rawStart), blocks.length));
    } else if (blocks.length > 0) {
      twStart = blocks.length - 1;
    } else {
      twStart = 0;
    }

    // Clear previous blocks
    this.renderer.clear();
    this.typewriter.reset();
    this.blocks = [];
    this.currentBlockIndex = 0;

    // Single-active contract: at most one active typewriter block (latest unresolved block).
    let activeIndex = -1;
    if (blocks.length > 0 && twStart < blocks.length) {
      for (let i = blocks.length - 1; i >= 0; i--) {
        if (!this._isDiagnosticsBlock(blocks[i])) {
          activeIndex = i;
          break;
        }
      }
    }

    for (let i = 0; i < blocks.length; i++) {
      const block = blocks[i];
      const transcriptStable = i !== activeIndex;
      this.blocks.push(block);
      this.renderer.render(block);

      if (this._isDiagnosticsBlock(block)) {
        continue;
      }

      if (!this.accessibility_mode) {
        if (transcriptStable) {
          const el = this.renderer.getBlockElement(block.id);
          if (el) {
            el.textContent = block.text || '';
          }
        } else {
          this.typewriter.startDelivery(block);
        }
      } else {
        const el = this.renderer.getBlockElement(block.id);
        if (el) {
          el.textContent = block.text || '';
        }
      }
    }
    this.currentBlockIndex = activeIndex >= 0 ? activeIndex : this.blocks.length;
  }

  /**
   * Append narrator block from WebSocket streaming
   *
   * Each chunk is one block; it becomes the active typewriter slice (ADR-0034 §5–§7).
   *
   * @param {Object} block - Scene block from narrator stream
   */
  appendNarratorBlock(block) {
    if (!block || !block.id || !block.text) {
      return;
    }

    // Add to blocks array
    this.blocks.push(block);

    // Render to DOM
    this.renderer.render(block);

    if (this._isDiagnosticsBlock(block)) {
      this.currentBlockIndex = this.blocks.length;
      return;
    }

    // Finish any in-progress delivery so only the new block animates.
    if (!this.accessibility_mode) {
      this.typewriter.revealAll();
    }

    // Start typewriter delivery (unless accessibility mode)
    if (!this.accessibility_mode) {
      this.typewriter.startDelivery(block);
      this.currentBlockIndex = this.blocks.length - 1;
    } else {
      const el = this.renderer.getBlockElement(block.id);
      if (el) {
        el.textContent = block.text;
      }
      this.currentBlockIndex = this.blocks.length;
    }
  }

  /**
   * Skip current block (user clicked "Skip")
   */
  skipCurrentBlock() {
    const tw = this.typewriter.getQueueState ? this.typewriter.getQueueState() : null;
    const activeId = tw && tw.current_block_id ? tw.current_block_id : null;
    if (!activeId) {
      return;
    }
    this.typewriter.skipBlock(activeId);
    this.currentBlockIndex = this.blocks.length;
  }

  /**
   * Reveal all blocks immediately (user clicked "Reveal All")
   */
  revealAll() {
    this.typewriter.revealAll();
  }

  /**
   * Toggle accessibility mode
   *
   * @param {boolean} enabled - Enable or disable accessibility mode
   */
  setAccessibilityMode(enabled) {
    this.accessibility_mode = !!enabled;

    if (enabled) {
      // Show all blocks immediately
      for (let block of this.blocks) {
        const el = this.renderer.getBlockElement(block.id);
        if (el) {
          el.textContent = block.text || '';
        }
      }
    }
  }

  /**
   * Get current state (for diagnostics)
   */
  getState() {
    return {
      blocks_count: this.blocks.length,
      current_block_index: this.currentBlockIndex,
      accessibility_mode: this.accessibility_mode,
      typewriter_state: this.typewriter.getQueueState(),
    };
  }
}

// Export for use
if (typeof window !== 'undefined') {
  window.BlocksOrchestrator = BlocksOrchestrator;
}
