/**
 * Unit tests for TypewriterEngine and VirtualClock
 * Tests deterministic time advancement and character delivery
 */

describe('VirtualClock', () => {
  describe('test mode', () => {
    test('should initialize with virtual_time = 0 in test mode', () => {
      const clock = new VirtualClock(true);
      expect(clock.now()).toBe(0);
    });

    test('should advance virtual time with advanceBy()', () => {
      const clock = new VirtualClock(true);
      clock.advanceBy(100);
      expect(clock.now()).toBe(100);

      clock.advanceBy(50);
      expect(clock.now()).toBe(150);
    });

    test('should notify listeners on time advance', () => {
      const clock = new VirtualClock(true);
      const listener = jest.fn();
      clock.onTick(listener);

      clock.advanceBy(100);

      expect(listener).toHaveBeenCalledWith(100);
    });

    test('should notify multiple listeners', () => {
      const clock = new VirtualClock(true);
      const listener1 = jest.fn();
      const listener2 = jest.fn();
      clock.onTick(listener1);
      clock.onTick(listener2);

      clock.advanceBy(50);

      expect(listener1).toHaveBeenCalledWith(50);
      expect(listener2).toHaveBeenCalledWith(50);
    });

    test('should throw error if advanceBy called in production mode', () => {
      const clock = new VirtualClock(false);
      expect(() => clock.advanceBy(100)).toThrow();
    });

    test('should handle listener errors gracefully', () => {
      const clock = new VirtualClock(true);
      const goodListener = jest.fn();
      const badListener = jest.fn(() => {
        throw new Error('Listener error');
      });
      clock.onTick(badListener);
      clock.onTick(goodListener);

      expect(() => clock.advanceBy(100)).not.toThrow();
      expect(goodListener).toHaveBeenCalled();
    });
  });

  describe('production mode', () => {
    test('should use performance.now() in production mode', () => {
      const clock = new VirtualClock(false);
      const time = clock.now();
      expect(typeof time).toBe('number');
      expect(time).toBeGreaterThan(0);
    });

    test('should throw error on advanceBy in production mode', () => {
      const clock = new VirtualClock(false);
      expect(() => clock.advanceBy(100)).toThrow(
        'VirtualClock.advanceBy() only available in test mode'
      );
    });
  });

  describe('onTick registration', () => {
    test('should throw error if callback is not a function', () => {
      const clock = new VirtualClock(true);
      expect(() => clock.onTick('not a function')).toThrow();
    });

    test('should allow multiple onTick calls', () => {
      const clock = new VirtualClock(true);
      const listener1 = jest.fn();
      const listener2 = jest.fn();
      const listener3 = jest.fn();

      clock.onTick(listener1);
      clock.onTick(listener2);
      clock.onTick(listener3);

      clock.advanceBy(25);

      expect(listener1).toHaveBeenCalled();
      expect(listener2).toHaveBeenCalled();
      expect(listener3).toHaveBeenCalled();
    });
  });
});

describe('TypewriterEngine', () => {
  let container;
  let engine;

  beforeEach(() => {
    // Set up DOM container
    container = document.createElement('div');
    document.body.appendChild(container);

    engine = new TypewriterEngine(true); // Test mode
  });

  afterEach(() => {
    engine.reset();
    document.body.removeChild(container);
  });

  describe('configuration', () => {
    test('should use default config', () => {
      expect(engine.config.characters_per_second).toBe(44);
      expect(engine.config.pause_before_ms).toBe(150);
      expect(engine.config.pause_after_ms).toBe(650);
      expect(engine.config.skippable).toBe(true);
    });

    test('should allow config updates', () => {
      engine.setConfig({
        characters_per_second: 50,
        skippable: false,
      });

      expect(engine.config.characters_per_second).toBe(50);
      expect(engine.config.skippable).toBe(false);
      expect(engine.config.pause_before_ms).toBe(150); // Unchanged
    });

    test('should handle partial config updates', () => {
      engine.setConfig({ characters_per_second: 100 });
      expect(engine.config.characters_per_second).toBe(100);
      expect(engine.config.pause_before_ms).toBe(150);
    });
  });

  describe('clock wiring (single active delivery)', () => {
    test('registers exactly one VirtualClock listener for the engine lifetime', () => {
      expect(engine.clock.listeners.length).toBe(1);
      engine.startDelivery({ id: 'a', text: 'aa' });
      engine.startDelivery({ id: 'b', text: 'bb' });
      engine.startDelivery({ id: 'c', text: 'cc' });
      expect(engine.clock.listeners.length).toBe(1);
    });
  });

  describe('startDelivery()', () => {
    test('should activate a block for delivery', () => {
      const block = {
        id: 'block-1',
        text: 'Hello world',
        delivery: {},
      };

      engine.startDelivery(block);

      const state = engine.getQueueState();
      expect(state.queue_length).toBe(1);
      expect(state.current_block_id).toBe('block-1');
    });

    test('should ignore invalid blocks', () => {
      engine.startDelivery(null);
      engine.startDelivery({});
      engine.startDelivery({ id: 'block-1' }); // No text

      const state = engine.getQueueState();
      expect(state.queue_length).toBe(0);
    });

    test('should calculate duration based on character count and speed', () => {
      const block = {
        id: 'block-1',
        text: 'x'.repeat(44), // 44 characters
        delivery: {},
      };

      engine.setConfig({ characters_per_second: 44 });
      engine.startDelivery(block);

      const state = engine.getQueueState();
      expect(state.current_block_id).toBe('block-1');
    });

    test('should replace active block when a newer block arrives', () => {
      const block1 = { id: 'block-1', text: 'First' };
      const block2 = { id: 'block-2', text: 'Second' };
      const block3 = { id: 'block-3', text: 'Third' };

      engine.startDelivery(block1);
      engine.startDelivery(block2);
      engine.startDelivery(block3);

      const state = engine.getQueueState();
      expect(state.queue_length).toBe(1);
      expect(state.current_block_id).toBe('block-3');
    });
  });

  describe('progressive rendering', () => {
    test('should render characters progressively', () => {
      const blockEl = document.createElement('div');
      blockEl.setAttribute('data-block-id', 'block-1');
      blockEl.textContent = 'Hello world'; // 11 characters
      container.appendChild(blockEl);

      const block = {
        id: 'block-1',
        text: 'Hello world',
        delivery: {},
      };

      engine.setConfig({ characters_per_second: 11 }); // 1 char per 1000ms
      engine.startDelivery(block);

      // Simulate time progression (11 characters * 1000ms / 11 cps = 1000ms)
      engine.clock.advanceBy(100); // 10% of duration
      let state = engine.getQueueState();
      expect(state.current_visible_chars).toBe(1); // ~1 character

      engine.clock.advanceBy(450); // 50% of duration
      state = engine.getQueueState();
      expect(state.current_visible_chars).toBeGreaterThanOrEqual(5);

      engine.clock.advanceBy(500); // 100% of duration
      state = engine.getQueueState();
      expect(state.queue_length).toBe(0);
      expect(state.current_block_id).toBeNull();
      expect(blockEl.textContent).toBe('Hello world');
    });

    test('should update DOM during rendering', () => {
      const blockEl = document.createElement('div');
      blockEl.setAttribute('data-block-id', 'block-1');
      container.appendChild(blockEl);

      const block = {
        id: 'block-1',
        text: 'Hello',
        delivery: {},
      };

      engine.setConfig({ characters_per_second: 5 }); // 1 char per 1000ms
      engine.startDelivery(block);

      engine.clock.advanceBy(500); // 50% of duration
      expect(blockEl.textContent).toBe('He'); // ~2 characters

      engine.clock.advanceBy(500); // 100% of duration
      expect(blockEl.textContent).toBe('Hello');
    });

    test('should complete block after full duration', () => {
      const block = {
        id: 'block-1',
        text: 'Test',
        delivery: {},
      };

      engine.startDelivery(block);

      let state = engine.getQueueState();
      expect(state.current_block_id).toBe('block-1');

      // Advance past full duration (4 chars * 1000 / 44 = ~91ms)
      engine.clock.advanceBy(100);

      state = engine.getQueueState();
      expect(state.queue_length).toBe(0);
      expect(state.current_block_id).toBeNull();
    });
  });

  describe('skipBlock()', () => {
    test('should complete current block immediately', () => {
      const blockEl = document.createElement('div');
      blockEl.setAttribute('data-block-id', 'block-1');
      container.appendChild(blockEl);

      const block = {
        id: 'block-1',
        text: 'Hello world',
        delivery: {},
      };

      engine.setConfig({ characters_per_second: 1 }); // Very slow
      engine.startDelivery(block);

      engine.clock.advanceBy(10); // Only 1 character visible

      engine.skipBlock('block-1');

      expect(blockEl.textContent).toBe('Hello world'); // All text shown
      let state = engine.getQueueState();
      expect(state.queue_length).toBe(0);
    });

    test('should clear active block after skip', () => {
      const block1 = {
        id: 'block-1',
        text: 'First',
        delivery: {},
      };
      const block2 = {
        id: 'block-2',
        text: 'Second',
        delivery: {},
      };

      engine.startDelivery(block1);
      engine.startDelivery(block2);
      engine.skipBlock('block-2');

      const state = engine.getQueueState();
      expect(state.current_block_id).toBeNull();
      expect(state.queue_length).toBe(0);
    });

    test('should not affect unrelated blocks', () => {
      const block1 = { id: 'block-1', text: 'First' };
      const block2 = { id: 'block-2', text: 'Second' };

      engine.startDelivery(block1);
      engine.startDelivery(block2);

      engine.skipBlock('block-999'); // Non-existent block

      const state = engine.getQueueState();
      expect(state.current_block_id).toBe('block-2'); // Latest block remains active
    });
  });

  describe('revealAll()', () => {
    test('should reveal active block immediately', () => {
      const blockEl = document.createElement('div');
      blockEl.setAttribute('data-block-id', 'block-2');
      container.appendChild(blockEl);

      const block1 = { id: 'block-1', text: 'First block' };
      const block2 = { id: 'block-2', text: 'Second block' };

      engine.setConfig({ characters_per_second: 1 });
      engine.startDelivery(block1);
      engine.startDelivery(block2);
      engine.clock.advanceBy(5);
      engine.revealAll();

      expect(blockEl.textContent).toBe('Second block');
    });

    test('should clear queue after reveal all', () => {
      const block1 = { id: 'block-1', text: 'First' };
      const block2 = { id: 'block-2', text: 'Second' };

      engine.startDelivery(block1);
      engine.startDelivery(block2);

      engine.revealAll();

      const state = engine.getQueueState();
      expect(state.queue_length).toBe(0);
      expect(state.current_block_id).toBeNull();
    });

    test('should work with no queued blocks', () => {
      expect(() => engine.revealAll()).not.toThrow();
    });
  });

  describe('reset()', () => {
    test('should clear queue and reset state', () => {
      const block = { id: 'block-1', text: 'Text' };
      engine.startDelivery(block);

      engine.reset();

      const state = engine.getQueueState();
      expect(state.queue_length).toBe(0);
      expect(state.current_block_id).toBeNull();
    });
  });

  describe('getQueueState()', () => {
    test('should return empty state when no blocks queued', () => {
      const state = engine.getQueueState();

      expect(state.current_block_id).toBeNull();
      expect(state.current_visible_chars).toBe(0);
      expect(state.queue_length).toBe(0);
      expect(state.queue).toEqual([]);
    });

    test('should return detailed state with the single active block', () => {
      const block1 = { id: 'block-1', text: 'Hello' };
      const block2 = { id: 'block-2', text: 'World' };

      engine.startDelivery(block1);
      engine.startDelivery(block2);

      const state = engine.getQueueState();

      expect(state.current_block_id).toBe('block-2');
      expect(state.queue_length).toBe(1);
      expect(state.queue).toHaveLength(1);
      expect(state.queue[0].block_id).toBe('block-2');
    });
  });
});
