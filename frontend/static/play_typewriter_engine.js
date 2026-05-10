/**
 * TypewriterEngine — Virtual clock + character-by-character delivery
 *
 * Responsibility: Manage typewriter animation with deterministic test mode.
 * VirtualClock allows tests to advance time manually via advanceBy().
 * Production mode uses requestAnimationFrame for smooth animation.
 *
 * Display text uses window.blockDisplayTextForShell (play_block_display_text.js).
 * Single active block; orchestrator owns slice sequencing via setOnDeliveryComplete.
 */

class VirtualClock {
  constructor(testMode = false) {
    this.test_mode = testMode;
    this.virtual_time = 0; // ms
    this.listeners = [];
    this.requestId = null;
  }

  advanceBy(ms) {
    if (!this.test_mode) {
      throw new Error('VirtualClock.advanceBy() only available in test mode');
    }
    this.virtual_time += ms;
    this._notifyListeners();
  }

  onTick(callback) {
    if (typeof callback !== 'function') {
      throw new Error('VirtualClock.onTick: callback must be a function');
    }
    this.listeners.push(callback);
  }

  now() {
    return this.test_mode ? this.virtual_time : performance.now();
  }

  start() {
    if (this.test_mode) {
      return;
    }
    const animate = () => {
      this._notifyListeners();
      this.requestId = requestAnimationFrame(animate);
    };
    this.requestId = requestAnimationFrame(animate);
  }

  stop() {
    if (this.requestId) {
      cancelAnimationFrame(this.requestId);
      this.requestId = null;
    }
  }

  _notifyListeners() {
    const currentTime = this.now();
    this.listeners.forEach((cb) => {
      try {
        cb(currentTime);
      } catch (e) {
        console.error('VirtualClock listener error:', e);
      }
    });
  }
}

function _shellDisplayText(block) {
  if (typeof blockDisplayTextForShell === 'function') {
    return String(blockDisplayTextForShell(block) ?? '');
  }
  if (!block) {
    return '';
  }
  return block.player_display_text != null ? String(block.player_display_text) : String(block.text ?? '');
}

class TypewriterEngine {
  constructor(testMode = false) {
    this.clock = new VirtualClock(testMode);
    this.queue = [];
    this.current_block = null;
    this.test_mode = testMode;
    this._onDeliveryComplete = null;
    this.config = {
      characters_per_second: 44,
      pause_before_ms: 150,
      pause_after_ms: 650,
      skippable: true,
    };
    this.clock.onTick((time) => this._onClockTick(time));
  }

  setConfig(config) {
    if (config && typeof config === 'object') {
      Object.assign(this.config, config);
    }
  }

  /**
   * Called with block id when the current block finishes naturally, skip, or empty immediate complete.
   * Orchestrator owns slice queue — engine stays single-active.
   *
   * @param {function(string): void | null} fn
   */
  setOnDeliveryComplete(fn) {
    this._onDeliveryComplete = typeof fn === 'function' ? fn : null;
  }

  startDelivery(block) {
    const text = _shellDisplayText(block);
    if (!block || !block.id) {
      return;
    }
    if (text.length === 0) {
      const el = document.querySelector(`[data-block-id="${block.id}"]`);
      if (el) {
        el.textContent = '';
      }
      const cb = this._onDeliveryComplete;
      if (cb) {
        cb(block.id);
      }
      return;
    }

    const cps = this.config.characters_per_second || 44;
    const duration = (text.length / cps) * 1000;

    const queueItem = {
      block_id: block.id,
      text,
      start_time: this.clock.now(),
      duration,
      visible_chars: 0,
    };

    this.queue = [queueItem];
    this.current_block = queueItem;
    if (!this.test_mode) {
      this.clock.start();
    }
  }

  _onClockTick(time) {
    if (!this.current_block) {
      return;
    }

    const elapsed = time - this.current_block.start_time;
    const visible_chars = Math.min(
      Math.floor((elapsed / this.current_block.duration) * this.current_block.text.length),
      this.current_block.text.length
    );

    this.current_block.visible_chars = visible_chars;
    this._renderBlock();

    if (visible_chars >= this.current_block.text.length) {
      this._completeCurrentBlock();
    }
  }

  _completeCurrentBlock() {
    if (!this.current_block) {
      return;
    }
    const bid = this.current_block.block_id;
    this.current_block.visible_chars = this.current_block.text.length;
    this._renderBlock();
    this.queue = [];
    this.current_block = null;
    this.clock.stop();
    const cb = this._onDeliveryComplete;
    if (cb) {
      cb(bid);
    }
  }

  skipBlock(blockId) {
    if (this.current_block && this.current_block.block_id === blockId) {
      this._completeCurrentBlock();
    }
  }

  revealAll() {
    if (this.current_block) {
      this.current_block.visible_chars = this.current_block.text.length;
      const el = document.querySelector(`[data-block-id="${this.current_block.block_id}"]`);
      if (el) {
        el.textContent = this.current_block.text;
      }
    }
    this.queue = [];
    this.current_block = null;
    this.clock.stop();
  }

  _renderBlock() {
    if (!this.current_block) {
      return;
    }

    const el = document.querySelector(`[data-block-id="${this.current_block.block_id}"]`);
    if (el) {
      el.textContent = this.current_block.text.substring(0, this.current_block.visible_chars);
    }
  }

  getQueueState() {
    return {
      current_block_id: this.current_block ? this.current_block.block_id : null,
      current_visible_chars: this.current_block ? this.current_block.visible_chars : 0,
      queue_length: this.queue.length,
      queue: this.queue.map((item) => ({
        block_id: item.block_id,
        visible_chars: item.visible_chars,
        total_chars: item.text.length,
      })),
    };
  }

  reset() {
    this.clock.stop();
    this.queue = [];
    this.current_block = null;
    this._onDeliveryComplete = null;
  }
}

if (typeof window !== 'undefined') {
  window.VirtualClock = VirtualClock;
  window.TypewriterEngine = TypewriterEngine;
}
