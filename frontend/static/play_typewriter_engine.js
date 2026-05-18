/**
 * TypewriterEngine — Cinematic per-character delivery (ADR-0046)
 *
 * Replaces the legacy substring writer with a per-char span model:
 *   - each character of the visible string is appended as <span class="char">.
 *   - a single <span class="play-cursor"> sits after the last revealed char.
 *   - schedule_at[k] is precomputed per char, mixing base interval + jitter
 *     (seeded by block id) + punctuation pause after the previous char.
 *
 * Determinism guarantee: when constructed with test_mode === true, the
 * engine bypasses jitter, punctuation pauses, lead-in, and cursor DOM, so
 * the existing test suite (frontend/tests/test_typewriter_engine.js) keeps
 * passing without modification. Char spans are still inserted under the
 * block element, so blockEl.textContent equals the progressively-typed
 * substring in both modes.
 *
 * Public surface (unchanged):
 *   - new TypewriterEngine(testMode)
 *   - setConfig(partial), setOnDeliveryComplete(fn)
 *   - startDelivery(block, options?)
 *   - skipBlock(id), revealAll(), reset()
 *   - getQueueState()
 *   - engine.clock.advanceBy(ms), engine.clock.now()
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

/* ── Beat profile map ─────────────────────────────────────────────────────
 * Each profile drives tempo, jitter, cursor variant, and atmosphere CSS.
 * Unknown beats fall back to `default`. Profiles are deliberately mutable
 * via setConfig({ beat_profiles: {…} }) for runtime tuning. */
const DEFAULT_BEAT_PROFILES = {
  default:     { cps: 44, jitter: 0.12, cursor: 'default',  atmosphere: 'beat--default',  pause_before: 0,   pause_after: 250 },
  boot:        { cps: 76, jitter: 0.04, cursor: 'boot',     atmosphere: 'beat--boot',     pause_before: 80,  pause_after: 220 },
  role_anchor: { cps: 28, jitter: 0.08, cursor: 'anchor',   atmosphere: 'beat--anchor',   pause_before: 320, pause_after: 480 },
  tension:     { cps: 62, jitter: 0.18, cursor: 'tension',  atmosphere: 'beat--tension',  pause_before: 0,   pause_after: 180 },
  escalation:  { cps: 62, jitter: 0.18, cursor: 'tension',  atmosphere: 'beat--tension',  pause_before: 0,   pause_after: 180 },
  dialogue:    { cps: 50, jitter: 0.14, cursor: 'dialogue', atmosphere: 'beat--dialogue', pause_before: 120, pause_after: 320 },
  action:      { cps: 74, jitter: 0.22, cursor: 'action',   atmosphere: 'beat--action',   pause_before: 0,   pause_after: 120 },
  reflection:  { cps: 30, jitter: 0.06, cursor: 'reflect',  atmosphere: 'beat--reflect',  pause_before: 220, pause_after: 520 },
};

/* Per-char punctuation pause table (ms). Applied AFTER a given char is
 * revealed (so the next char arrives later). */
const PUNCTUATION_PAUSE_MS = {
  '.': 320,
  '!': 360,
  '?': 360,
  ',': 130,
  ';': 150,
  ':': 130,
  '—': 180,
  '–': 140,
  '\n': 200,
};

/* Deterministic, block-id-seeded PRNG (mulberry32). Same id → same rhythm.  */
function _seedFromString(s) {
  let h = 2166136261 >>> 0;
  const str = String(s || '');
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h || 1;
}
function _mulberry32(seed) {
  let t = seed >>> 0;
  return function () {
    t = (t + 0x6D2B79F5) >>> 0;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

class TypewriterEngine {
  constructor(testMode = false) {
    this.clock = new VirtualClock(testMode);
    this.queue = [];
    this.current_block = null;
    this.test_mode = testMode;
    this._onDeliveryComplete = null;
    this._scroll_frame = null;
    this._pending_scroll_container = null;
    this.config = {
      characters_per_second: 44,
      pause_before_ms: 150,
      pause_after_ms: 650,
      skippable: true,
      cinematic: !testMode, // jitter + punctuation pauses + lead-in
      beat_profiles: DEFAULT_BEAT_PROFILES,
    };
    this.clock.onTick((time) => this._onClockTick(time));
  }

  setConfig(config) {
    if (config && typeof config === 'object') {
      Object.assign(this.config, config);
    }
  }

  setOnDeliveryComplete(fn) {
    this._onDeliveryComplete = typeof fn === 'function' ? fn : null;
  }

  _profileFor(block) {
    const beat = String((block && block.narration_beat) || '').trim().toLowerCase();
    const profiles = this.config.beat_profiles || DEFAULT_BEAT_PROFILES;
    return profiles[beat] || profiles.default || DEFAULT_BEAT_PROFILES.default;
  }

  _resolveBlockElement(blockId) {
    return document.querySelector(`[data-block-id="${blockId}"]`);
  }

  _resolveScrollContainer(el) {
    let current = el;
    while (current) {
      if (
        current.getAttribute &&
        (
          current.getAttribute('data-typewriter-shell') === 'true' ||
          current.classList.contains('play-story-window__body')
        )
      ) {
        return current;
      }
      current = current.parentElement;
    }
    return null;
  }

  _scrollCurrentLineIntoView(item) {
    if (!item || !item.block_el) return;
    const container = this._resolveScrollContainer(item.block_el);
    if (!container) return;

    const applyScroll = () => {
      container.scrollTop = container.scrollHeight;
    };

    if (this.test_mode || typeof requestAnimationFrame !== 'function') {
      applyScroll();
      return;
    }

    this._pending_scroll_container = container;
    if (this._scroll_frame !== null) return;
    this._scroll_frame = requestAnimationFrame(() => {
      const target = this._pending_scroll_container;
      this._pending_scroll_container = null;
      this._scroll_frame = null;
      if (target) {
        target.scrollTop = target.scrollHeight;
      }
    });
  }

  _resetBlockDom(el, profile) {
    if (!el) return null;
    el.textContent = '';
    if (profile && profile.atmosphere) {
      for (const cls of Array.from(el.classList)) {
        if (cls.startsWith('beat--')) el.classList.remove(cls);
      }
      el.classList.add(profile.atmosphere);
    }
    if (this.test_mode) return null; // no cursor DOM in tests
    const cursor = document.createElement('span');
    cursor.className = 'play-cursor';
    cursor.setAttribute('aria-hidden', 'true');
    cursor.setAttribute('data-cursor-variant', (profile && profile.cursor) || 'default');
    el.appendChild(cursor);
    return cursor;
  }

  startDelivery(block, options) {
    const text = _shellDisplayText(block);
    if (!block || !block.id) {
      return;
    }
    const profile = this._profileFor(block);
    const deliveryCps = Number(block && block.delivery && block.delivery.characters_per_second);
    const cps = (options && options.cps_override)
      || (Number.isFinite(deliveryCps) && deliveryCps > 0 ? deliveryCps : null)
      || this.config.characters_per_second
      || profile.cps
      || 44;
    const base_interval = 1000 / cps;
    const cinematic = !!this.config.cinematic && !this.test_mode;
    const lead_in = cinematic
      ? Math.max(0, Number((options && options.lead_in_ms) || profile.pause_before || 0))
      : 0;

    if (text.length === 0) {
      const el = this._resolveBlockElement(block.id);
      if (el) {
        this._resetBlockDom(el, profile);
      }
      const cb = this._onDeliveryComplete;
      if (cb) cb(block.id);
      return;
    }

    const el = this._resolveBlockElement(block.id);
    const cursorEl = this._resetBlockDom(el, profile);

    const rand = cinematic ? _mulberry32(_seedFromString(block.id)) : null;
    const jitterAmp = cinematic ? Math.max(0, Number(profile.jitter || 0)) : 0;

    const scheduled_at = new Array(text.length);
    let acc = lead_in;
    for (let k = 0; k < text.length; k++) {
      const prev = k === 0 ? '' : text[k - 1];
      const punctuation = cinematic ? (PUNCTUATION_PAUSE_MS[prev] || 0) : 0;
      const jitter = cinematic && rand ? base_interval * jitterAmp * (rand() * 2 - 1) : 0;
      acc += base_interval + punctuation + jitter;
      scheduled_at[k] = acc;
    }

    const start_time = this.clock.now();
    const duration = scheduled_at[scheduled_at.length - 1] || 0;

    const queueItem = {
      block_id: block.id,
      text,
      start_time,
      duration,
      scheduled_at,
      visible_chars: 0,
      block_el: el || null,
      cursor_el: cursorEl,
      profile,
    };

    this.queue = [queueItem];
    this.current_block = queueItem;
    if (!this.test_mode) {
      this.clock.start();
    }
  }

  _onClockTick(time) {
    const item = this.current_block;
    if (!item) return;

    const elapsed = time - item.start_time;
    let next_visible = item.visible_chars;
    while (
      next_visible < item.text.length &&
      item.scheduled_at[next_visible] <= elapsed
    ) {
      next_visible++;
    }

    if (next_visible !== item.visible_chars) {
      this._appendChars(item, item.visible_chars, next_visible);
      item.visible_chars = next_visible;
    }

    if (next_visible >= item.text.length) {
      this._completeCurrentBlock();
    }
  }

  _appendChars(item, from, to) {
    if (!item.block_el) {
      item.block_el = this._resolveBlockElement(item.block_id);
      if (!item.block_el) return;
    }
    const frag = document.createDocumentFragment();
    for (let k = from; k < to; k++) {
      const span = document.createElement('span');
      span.className = 'char';
      span.setAttribute('data-i', String(k));
      const ch = item.text[k];
      // Whitespace must be visible to layout but should still animate.
      if (ch === '\n') {
        span.classList.add('char--break');
        span.appendChild(document.createElement('br'));
      } else if (ch === ' ') {
        span.classList.add('char--space');
        span.textContent = ' ';
      } else {
        span.textContent = ch;
      }
      frag.appendChild(span);
    }
    // Insert before cursor if one exists; else append.
    if (item.cursor_el && item.cursor_el.parentNode === item.block_el) {
      item.block_el.insertBefore(frag, item.cursor_el);
      // Pulse cursor on reveal
      item.cursor_el.classList.remove('play-cursor--pulse');
      // Trigger reflow so animation restarts
      void item.cursor_el.offsetWidth;
      item.cursor_el.classList.add('play-cursor--pulse');
    } else {
      item.block_el.appendChild(frag);
    }
    this._scrollCurrentLineIntoView(item);
  }

  _completeCurrentBlock() {
    const item = this.current_block;
    if (!item) return;
    const bid = item.block_id;
    if (item.visible_chars < item.text.length) {
      this._appendChars(item, item.visible_chars, item.text.length);
      item.visible_chars = item.text.length;
    }
    if (item.cursor_el && item.cursor_el.parentNode === item.block_el) {
      item.cursor_el.classList.add('play-cursor--settle');
      // Cursor fades out via CSS animation; leave DOM for animation to finish.
    }
    this.queue = [];
    this.current_block = null;
    this.clock.stop();
    const cb = this._onDeliveryComplete;
    if (cb) cb(bid);
  }

  skipBlock(blockId) {
    if (this.current_block && this.current_block.block_id === blockId) {
      this._completeCurrentBlock();
    }
  }

  revealAll() {
    const item = this.current_block;
    if (item) {
      if (item.visible_chars < item.text.length) {
        this._appendChars(item, item.visible_chars, item.text.length);
        item.visible_chars = item.text.length;
      }
      if (item.cursor_el && item.cursor_el.parentNode === item.block_el) {
        item.cursor_el.classList.add('play-cursor--settle');
      }
    }
    this.queue = [];
    this.current_block = null;
    this.clock.stop();
  }

  _renderBlock() {
    // No-op: rendering is push-based via _appendChars. Kept for backward
    // compatibility with any external caller that might invoke it.
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
    if (this._scroll_frame !== null && typeof cancelAnimationFrame === 'function') {
      cancelAnimationFrame(this._scroll_frame);
    }
    this._scroll_frame = null;
    this._pending_scroll_container = null;
    this._onDeliveryComplete = null;
  }
}

if (typeof window !== 'undefined') {
  window.VirtualClock = VirtualClock;
  window.TypewriterEngine = TypewriterEngine;
  window.TYPEWRITER_BEAT_PROFILES = DEFAULT_BEAT_PROFILES;
  window.TYPEWRITER_PUNCTUATION_PAUSE_MS = PUNCTUATION_PAUSE_MS;
}
