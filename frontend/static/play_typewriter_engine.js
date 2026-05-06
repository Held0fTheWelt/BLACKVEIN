/**
 * TypewriterEngine — Virtual clock + character-by-character delivery
 *
 * Responsibility: Manage typewriter animation with deterministic test mode.
 * VirtualClock allows tests to advance time manually via advanceBy().
 * Production mode uses requestAnimationFrame for smooth animation.
 */

class VirtualClock {
  constructor(testMode = false) {
    this.test_mode = testMode;
    this.virtual_time = 0; // ms
    this.listeners = [];
    this.requestId = null;
  }

  /**
   * Advance virtual time (test mode only)
   *
   * @param {number} ms - Milliseconds to advance
   */
  advanceBy(ms) {
    if (!this.test_mode) {
      throw new Error('VirtualClock.advanceBy() only available in test mode');
    }
    this.virtual_time += ms;
    this._notifyListeners();
  }

  /**
   * Register callback for time ticks
   *
   * @param {Function} callback - Called with current time on each tick
   */
  onTick(callback) {
    if (typeof callback !== 'function') {
      throw new Error('VirtualClock.onTick: callback must be a function');
    }
    this.listeners.push(callback);
  }

  /**
   * Get current time
   *
   * @returns {number} Current time in milliseconds
   */
  now() {
    return this.test_mode ? this.virtual_time : performance.now();
  }

  /**
   * Start animation loop (production mode only)
   */
  start() {
    if (this.test_mode) {
      return; // Test mode doesn't use animation loop
    }
    const animate = () => {
      this._notifyListeners();
      this.requestId = requestAnimationFrame(animate);
    };
    this.requestId = requestAnimationFrame(animate);
  }

  /**
   * Stop animation loop
   */
  stop() {
    if (this.requestId) {
      cancelAnimationFrame(this.requestId);
      this.requestId = null;
    }
  }

  /**
   * Notify all listeners of time update
   */
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

class TypewriterEngine {
  constructor(testMode = false) {
    this.clock = new VirtualClock(testMode);
    this.queue = []; // [{block_id, text, start_time, duration, visible_chars}]
    this.current_block = null;
    this.test_mode = testMode;
    this.config = {
      characters_per_second: 44,
      pause_before_ms: 150,
      pause_after_ms: 650,
      skippable: true,
    };
    // One listener for the lifetime of the engine — avoids duplicate onTick handlers per block.
    this.clock.onTick((time) => this._onClockTick(time));
  }

  /**
   * Update typewriter configuration
   *
   * @param {Object} config - Delivery config (characters_per_second, pause_before_ms, etc.)
   */
  setConfig(config) {
    if (config && typeof config === 'object') {
      Object.assign(this.config, config);
    }
  }

  /**
   * Start delivery of a block
   *
   * @param {Object} block - Block with id, text, delivery config
   */
  startDelivery(block) {
    if (!block || !block.id || !block.text) {
      return;
    }

    const cps = this.config.characters_per_second || 44;
    const duration = (block.text.length / cps) * 1000; // ms

    const queueItem = {
      block_id: block.id,
      text: block.text,
      start_time: this.clock.now(),
      duration: duration,
      visible_chars: 0,
    };

    this.queue.push(queueItem);
    this._processQueue();
  }

  /**
   * Process the delivery queue
   */
  _processQueue() {
    if (this.queue.length === 0 || this.current_block) {
      return;
    }

    this.current_block = this.queue[0];

    if (!this.test_mode) {
      this.clock.start();
    }
  }

  /**
   * Single clock tick handler (registered once in constructor).
   */
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

  /**
   * Complete current block and move to next
   */
  _completeCurrentBlock() {
    if (this.current_block) {
      this.current_block.visible_chars = this.current_block.text.length;
      this._renderBlock();
      this.queue.shift();
      this.current_block = null;
      this._processQueue();
    }
  }

  /**
   * Skip current block (user clicked "Skip")
   *
   * @param {string} blockId - Block ID to skip
   */
  skipBlock(blockId) {
    if (this.current_block && this.current_block.block_id === blockId) {
      this._completeCurrentBlock();
    }
  }

  /**
   * Reveal all queued blocks immediately
   */
  revealAll() {
    for (const block of this.queue) {
      block.visible_chars = block.text.length;
      const el = document.querySelector(`[data-block-id="${block.block_id}"]`);
      if (el) {
        el.textContent = block.text;
      }
    }
    this._renderBlock();
    this.queue = [];
    this.current_block = null;
    this.clock.stop();
  }

  /**
   * Update DOM element with current visible characters
   */
  _renderBlock() {
    if (!this.current_block) {
      return;
    }

    const el = document.querySelector(`[data-block-id="${this.current_block.block_id}"]`);
    if (el) {
      el.textContent = this.current_block.text.substring(0, this.current_block.visible_chars);
    }
  }

  /**
   * Get current queue state (for testing/diagnostics)
   */
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

  /**
   * Reset engine state
   */
  reset() {
    this.clock.stop();
    this.queue = [];
    this.current_block = null;
  }
}

// Export for use
if (typeof window !== 'undefined') {
  window.VirtualClock = VirtualClock;
  window.TypewriterEngine = TypewriterEngine;
}
