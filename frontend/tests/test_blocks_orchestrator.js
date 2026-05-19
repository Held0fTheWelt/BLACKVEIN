/**
 * Unit tests for BlocksOrchestrator
 * Tests state management and coordination between modules
 */

describe('BlocksOrchestrator', () => {
  let container;
  let mockRenderer;
  let mockTypewriter;
  let orchestrator;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);

    // Create mock renderer
    mockRenderer = {
      render: jest.fn((block) => {
        const el = document.createElement('div');
        el.setAttribute('data-block-id', block.id);
        el.textContent = block.text || '';
        container.appendChild(el);
        return el;
      }),
      getBlockElement: jest.fn((id) => {
        return container.querySelector(`[data-block-id="${id}"]`);
      }),
      clear: jest.fn(() => {
        container.innerHTML = '';
      }),
    };

    // Create mock typewriter
    mockTypewriter = {
      startDelivery: jest.fn(),
      skipBlock: jest.fn(),
      revealAll: jest.fn(),
      reset: jest.fn(),
      setOnDeliveryComplete: jest.fn(),
      getQueueState: jest.fn(() => ({
        current_block_id: null,
        queue_length: 0,
      })),
    };

    orchestrator = new BlocksOrchestrator(mockRenderer, mockTypewriter);
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  describe('initialization', () => {
    test('should require renderer and typewriter', () => {
      expect(() => new BlocksOrchestrator(null, mockTypewriter)).toThrow();
      expect(() => new BlocksOrchestrator(mockRenderer, null)).toThrow();
    });

    test('should initialize with empty blocks', () => {
      expect(orchestrator.blocks).toEqual([]);
      expect(orchestrator.currentBlockIndex).toBe(0);
      expect(orchestrator.accessibility_mode).toBe(false);
    });

    test('should optionally accept controls', () => {
      const mockControls = {};
      const orch = new BlocksOrchestrator(mockRenderer, mockTypewriter, mockControls);
      expect(orch.controls).toBe(mockControls);
    });
  });

  describe('loadTurn()', () => {
    test('should load and render blocks from HTTP response', () => {
      const response = {
        visible_scene_output: {
          blocks: [
            { id: 'block-1', block_type: 'narrator', text: 'First' },
            { id: 'block-2', block_type: 'actor_line', text: 'Second' },
          ],
        },
      };

      orchestrator.loadTurn(response);

      expect(orchestrator.blocks).toHaveLength(2);
      // Default twStart = last index: stable prefix + first slice card → both mounted.
      expect(mockRenderer.render).toHaveBeenCalledTimes(2);
      expect(mockTypewriter.startDelivery).toHaveBeenCalledTimes(1);
      expect(mockTypewriter.startDelivery).toHaveBeenCalledWith(
        expect.objectContaining({ id: 'block-2', text: 'Second' }),
      );
    });

    test('with typewriter_slice_start_index 0, sequences both blocks after completion callback', () => {
      let onSliceComplete;
      mockTypewriter.setOnDeliveryComplete.mockImplementation((cb) => {
        onSliceComplete = cb;
      });

      const response = {
        visible_scene_output: {
          typewriter_slice_start_index: 0,
          blocks: [
            { id: 'block-1', block_type: 'narrator', text: 'First' },
            { id: 'block-2', block_type: 'actor_line', text: 'Second' },
          ],
        },
      };

      orchestrator.loadTurn(response);

      expect(mockTypewriter.setOnDeliveryComplete).toHaveBeenCalled();
      expect(mockRenderer.render).toHaveBeenCalledTimes(1);
      expect(container.querySelectorAll('[data-block-id]').length).toBe(1);
      expect(mockTypewriter.startDelivery).toHaveBeenCalledTimes(1);
      expect(mockTypewriter.startDelivery).toHaveBeenNthCalledWith(
        1,
        expect.objectContaining({ id: 'block-1', text: 'First' }),
      );
      const el = container.querySelector('[data-block-id="block-1"]');
      expect(el.textContent).toBe('');

      expect(typeof onSliceComplete).toBe('function');
      onSliceComplete('block-1');

      expect(mockRenderer.render).toHaveBeenCalledTimes(2);
      expect(container.querySelectorAll('[data-block-id]').length).toBe(2);
      expect(mockTypewriter.startDelivery).toHaveBeenCalledTimes(2);
      expect(mockTypewriter.startDelivery).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({ id: 'block-2', text: 'Second' }),
      );
    });

    test('with typewriter_slice_start_index 1, prior block full text then types the rest', () => {
      const response = {
        visible_scene_output: {
          typewriter_slice_start_index: 1,
          blocks: [
            { id: 'block-1', block_type: 'narrator', text: 'Prior' },
            { id: 'block-2', block_type: 'actor_line', text: 'New' },
          ],
        },
      };

      orchestrator.loadTurn(response);

      expect(mockTypewriter.startDelivery).toHaveBeenCalledTimes(1);
      expect(mockTypewriter.startDelivery).toHaveBeenCalledWith(
        expect.objectContaining({ id: 'block-2', text: 'New' }),
      );
      const el = container.querySelector('[data-block-id="block-1"]');
      expect(el.textContent).toBe('Prior');
      expect(mockRenderer.render).toHaveBeenCalledTimes(2);
      expect(container.querySelector('[data-block-id="block-2"]')).not.toBeNull();
    });

    test('with typewriter_slice_start_index 1, defers third and later slice cards until prior delivery completes', () => {
      let onSliceComplete;
      mockTypewriter.setOnDeliveryComplete.mockImplementation((cb) => {
        onSliceComplete = cb;
      });

      const response = {
        visible_scene_output: {
          typewriter_slice_start_index: 1,
          blocks: [
            { id: 'block-1', block_type: 'narrator', text: 'Stable' },
            { id: 'block-2', block_type: 'actor_line', text: 'SliceA' },
            { id: 'block-3', block_type: 'narrator', text: 'SliceB' },
          ],
        },
      };

      orchestrator.loadTurn(response);

      expect(mockRenderer.render).toHaveBeenCalledTimes(2);
      expect(container.querySelector('[data-block-id="block-1"]')).not.toBeNull();
      expect(container.querySelector('[data-block-id="block-2"]')).not.toBeNull();
      expect(container.querySelector('[data-block-id="block-3"]')).toBeNull();
      expect(mockTypewriter.startDelivery).toHaveBeenNthCalledWith(
        1,
        expect.objectContaining({ id: 'block-2', text: 'SliceA' }),
      );

      onSliceComplete('block-2');
      expect(mockRenderer.render).toHaveBeenCalledTimes(3);
      expect(container.querySelector('[data-block-id="block-3"]')).not.toBeNull();
      expect(mockTypewriter.startDelivery).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({ id: 'block-3', text: 'SliceB' }),
      );
    });

    test('with typewriter_slice_start_index 0, typing uses player_display_text when set', () => {
      let onSliceComplete;
      mockTypewriter.setOnDeliveryComplete.mockImplementation((cb) => {
        onSliceComplete = cb;
      });

      const response = {
        visible_scene_output: {
          typewriter_slice_start_index: 0,
          blocks: [
            {
              id: 'b1',
              block_type: 'narrator',
              player_display_text: 'Shell one',
              text: 'ignored',
            },
            {
              id: 'b2',
              block_type: 'actor_line',
              player_display_text: 'Shell two',
              text: 'ignored2',
            },
          ],
        },
      };

      orchestrator.loadTurn(response);

      expect(mockTypewriter.startDelivery).toHaveBeenNthCalledWith(
        1,
        expect.objectContaining({ id: 'b1', player_display_text: 'Shell one' }),
      );

      onSliceComplete('b1');
      expect(mockTypewriter.startDelivery).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({ id: 'b2', player_display_text: 'Shell two' }),
      );
    });

    test('should clear previous blocks before loading', () => {
      const block1 = {
        visible_scene_output: {
          blocks: [{ id: 'block-1', block_type: 'narrator', text: 'First' }],
        },
      };
      const block2 = {
        visible_scene_output: {
          blocks: [{ id: 'block-2', block_type: 'narrator', text: 'Second' }],
        },
      };

      orchestrator.loadTurn(block1);
      expect(orchestrator.blocks).toHaveLength(1);

      orchestrator.loadTurn(block2);

      expect(mockRenderer.clear).toHaveBeenCalled();
      expect(mockTypewriter.reset).toHaveBeenCalled();
      expect(orchestrator.blocks).toHaveLength(1);
      expect(orchestrator.blocks[0].id).toBe('block-2');
    });

    test('should handle empty blocks array', () => {
      const response = {
        visible_scene_output: {
          blocks: [],
        },
      };

      orchestrator.loadTurn(response);

      expect(orchestrator.blocks).toHaveLength(0);
      expect(mockRenderer.render).not.toHaveBeenCalled();
    });

    test('should handle missing visible_scene_output', () => {
      orchestrator.loadTurn({});
      expect(orchestrator.blocks).toHaveLength(0);

      orchestrator.loadTurn(null);
      expect(orchestrator.blocks).toHaveLength(0);
    });

    test('should reset currentBlockIndex on load', () => {
      orchestrator.currentBlockIndex = 5;

      orchestrator.loadTurn({
        visible_scene_output: {
          blocks: [{ id: 'block-1', block_type: 'narrator', text: 'Text' }],
        },
      });

      expect(orchestrator.currentBlockIndex).toBe(0);
    });

    test('should respect accessibility mode during load', () => {
      orchestrator.setAccessibilityMode(true);

      orchestrator.loadTurn({
        visible_scene_output: {
          blocks: [{ id: 'block-1', block_type: 'narrator', text: 'Text' }],
        },
      });

      expect(mockTypewriter.startDelivery).not.toHaveBeenCalled();
      const el = container.querySelector('[data-block-id="block-1"]');
      expect(el.textContent).toBe('Text');
    });
  });

  describe('appendNarratorBlock()', () => {
    test('should append block to blocks array', () => {
      const block = { id: 'block-1', block_type: 'narrator', text: 'New' };

      orchestrator.appendNarratorBlock(block);

      expect(orchestrator.blocks).toHaveLength(1);
      expect(orchestrator.blocks[0]).toBe(block);
    });

    test('should render block to DOM', () => {
      const block = { id: 'block-1', block_type: 'narrator', text: 'Text' };

      orchestrator.appendNarratorBlock(block);

      expect(mockRenderer.render).toHaveBeenCalledWith(block);
    });

    test('should start typewriter delivery', () => {
      const block = { id: 'block-1', block_type: 'narrator', text: 'Text' };

      orchestrator.appendNarratorBlock(block);

      expect(mockTypewriter.revealAll).toHaveBeenCalled();
      expect(mockTypewriter.startDelivery).toHaveBeenCalledWith(block);
    });

    test('should append multiple blocks in order', () => {
      const block1 = { id: 'block-1', block_type: 'narrator', text: 'First' };
      const block2 = { id: 'block-2', block_type: 'actor_line', text: 'Second' };

      orchestrator.appendNarratorBlock(block1);
      orchestrator.appendNarratorBlock(block2);

      expect(orchestrator.blocks).toHaveLength(2);
      expect(orchestrator.blocks[0].id).toBe('block-1');
      expect(orchestrator.blocks[1].id).toBe('block-2');
      expect(mockTypewriter.revealAll).toHaveBeenCalled();
    });

    test('should ignore invalid blocks', () => {
      orchestrator.appendNarratorBlock(null);
      orchestrator.appendNarratorBlock({});
      orchestrator.appendNarratorBlock({ id: 'block-1' }); // No text

      expect(orchestrator.blocks).toHaveLength(0);
    });

    test('should respect accessibility mode', () => {
      orchestrator.setAccessibilityMode(true);
      const block = { id: 'block-1', block_type: 'narrator', text: 'Text' };

      orchestrator.appendNarratorBlock(block);

      expect(mockTypewriter.startDelivery).not.toHaveBeenCalled();
      const el = container.querySelector('[data-block-id="block-1"]');
      expect(el.textContent).toBe('Text');
    });
  });

  describe('skipCurrentBlock()', () => {
    test('should skip current block and invoke skipBlock with active id', () => {
      mockTypewriter.getQueueState.mockReturnValue({ current_block_id: 'block-2' });

      orchestrator.skipCurrentBlock();

      expect(mockTypewriter.skipBlock).toHaveBeenCalledWith('block-2');
    });

    test('should handle skip beyond blocks array', () => {
      orchestrator.blocks = [{ id: 'block-1', text: 'Only' }];
      orchestrator.currentBlockIndex = 1;
      mockTypewriter.getQueueState.mockReturnValue({ current_block_id: null });

      expect(() => orchestrator.skipCurrentBlock()).not.toThrow();
      expect(mockTypewriter.skipBlock).not.toHaveBeenCalled();
    });
  });

  describe('revealAll()', () => {
    test('should call typewriter revealAll', () => {
      orchestrator.revealAll();
      expect(mockTypewriter.revealAll).toHaveBeenCalled();
    });

    test('should clear slice queue after revealing pending slice blocks', () => {
      orchestrator.loadTurn({
        visible_scene_output: {
          typewriter_slice_start_index: 0,
          blocks: [
            { id: 'a', block_type: 'narrator', text: 'First' },
            { id: 'b', block_type: 'narrator', text: 'Second' },
          ],
        },
      });
      expect(orchestrator.sliceQueue.length).toBe(2);

      orchestrator.revealAll();

      expect(mockTypewriter.revealAll).toHaveBeenCalled();
      expect(orchestrator.sliceQueue.length).toBe(0);
      expect(orchestrator.currentSliceIndex).toBe(0);
    });

    test('revealAll mounts deferred slice blocks and fills full text', () => {
      orchestrator.loadTurn({
        visible_scene_output: {
          typewriter_slice_start_index: 0,
          blocks: [
            { id: 'a', block_type: 'narrator', text: 'First' },
            { id: 'b', block_type: 'narrator', text: 'Second' },
          ],
        },
      });

      expect(mockRenderer.render).toHaveBeenCalledTimes(1);
      expect(container.querySelector('[data-block-id="b"]')).toBeNull();

      orchestrator.revealAll();

      expect(mockRenderer.render).toHaveBeenCalledTimes(2);
      const elB = container.querySelector('[data-block-id="b"]');
      expect(elB).not.toBeNull();
      expect(elB.textContent).toBe('Second');
      const elA = container.querySelector('[data-block-id="a"]');
      expect(elA.textContent).toBe('First');
    });

    test('should work with no blocks', () => {
      expect(() => orchestrator.revealAll()).not.toThrow();
    });
  });

  describe('setAccessibilityMode()', () => {
    test('should toggle accessibility mode', () => {
      expect(orchestrator.accessibility_mode).toBe(false);

      orchestrator.setAccessibilityMode(true);
      expect(orchestrator.accessibility_mode).toBe(true);

      orchestrator.setAccessibilityMode(false);
      expect(orchestrator.accessibility_mode).toBe(false);
    });

    test('should show all text when enabled', () => {
      orchestrator.blocks = [
        { id: 'block-1', block_type: 'narrator', text: 'First' },
        { id: 'block-2', block_type: 'actor_line', text: 'Second' },
      ];

      // Render blocks
      orchestrator.blocks.forEach((b) => mockRenderer.render(b));

      orchestrator.setAccessibilityMode(true);

      const el1 = container.querySelector('[data-block-id="block-1"]');
      const el2 = container.querySelector('[data-block-id="block-2"]');

      expect(el1.textContent).toBe('First');
      expect(el2.textContent).toBe('Second');
    });

    test('when enabled after deferred loadTurn, mounts all blocks and fills full transcript', () => {
      orchestrator.loadTurn({
        visible_scene_output: {
          typewriter_slice_start_index: 0,
          blocks: [
            { id: 'block-1', block_type: 'narrator', text: 'First' },
            { id: 'block-2', block_type: 'actor_line', text: 'Second' },
          ],
        },
      });

      expect(mockRenderer.render).toHaveBeenCalledTimes(1);
      expect(orchestrator.blocks).toHaveLength(2);

      orchestrator.setAccessibilityMode(true);

      expect(mockRenderer.render).toHaveBeenCalledTimes(2);
      expect(container.querySelectorAll('[data-block-id]').length).toBe(2);
      expect(container.querySelector('[data-block-id="block-1"]').textContent).toBe('First');
      expect(container.querySelector('[data-block-id="block-2"]').textContent).toBe('Second');
    });

    test('should coerce truthy/falsy values', () => {
      orchestrator.setAccessibilityMode(1);
      expect(orchestrator.accessibility_mode).toBe(true);

      orchestrator.setAccessibilityMode('');
      expect(orchestrator.accessibility_mode).toBe(false);

      orchestrator.setAccessibilityMode(null);
      expect(orchestrator.accessibility_mode).toBe(false);
    });
  });

  describe('getState()', () => {
    test('should return current orchestrator state', () => {
      orchestrator.blocks = [
        { id: 'block-1', text: 'First' },
        { id: 'block-2', text: 'Second' },
      ];
      orchestrator.currentBlockIndex = 1;
      orchestrator.accessibility_mode = true;

      const state = orchestrator.getState();

      expect(state.blocks_count).toBe(2);
      expect(state.current_block_index).toBe(1);
      expect(state.accessibility_mode).toBe(true);
      expect(state.typewriter_state).toBeDefined();
    });
  });

  describe('integration with real modules', () => {
    test('should work with real BlockRenderer', () => {
      const realContainer = document.createElement('div');
      document.body.appendChild(realContainer);

      const realRenderer = new BlockRenderer(realContainer);
      const realTypewriter = new TypewriterEngine(true);
      const orch = new BlocksOrchestrator(realRenderer, realTypewriter);

      const response = {
        visible_scene_output: {
          typewriter_slice_start_index: 0,
          blocks: [
            { id: 'b1', block_type: 'narrator', text: 'First' },
            { id: 'b2', block_type: 'actor_line', text: 'Second' },
          ],
        },
      };

      orch.loadTurn(response);

      expect(realContainer.children.length).toBe(1);
      expect(realContainer.children[0].getAttribute('data-block-id')).toBe('b1');

      document.body.removeChild(realContainer);
    });
  });

  describe('diagnostics block filtering', () => {
    test('should not enqueue diagnostics blocks for typewriter', () => {
      orchestrator.loadTurn({
        visible_scene_output: {
          typewriter_slice_start_index: 0,
          blocks: [
            { id: 'b1', block_type: 'narrator', text: 'Scene' },
            { id: 'b2', block_type: 'diagnostic_trace', text: 'debug payload' },
          ],
        },
      });

      expect(mockTypewriter.startDelivery).toHaveBeenCalledTimes(1);
      expect(mockTypewriter.startDelivery).toHaveBeenCalledWith(
        expect.objectContaining({ id: 'b1' }),
      );
    });
  });

  // ── Phase 2 Stage B→C: Event Stream Adapter ──────────────────────────────

  describe('_blockFromStreamEvent()', () => {
    test('extracts block_payload and adds trace fields', () => {
      const event = {
        event_id: 'evt-1',
        tick_id: 'tick-1',
        lane: 'visible_scene_output',
        block_payload: { id: 'b1', block_type: 'narrator', text: 'Hello.' },
      };
      const block = orchestrator._blockFromStreamEvent(event);
      expect(block.id).toBe('b1');
      expect(block.block_type).toBe('narrator');
      expect(block.text).toBe('Hello.');
      expect(block._stream_event_id).toBe('evt-1');
      expect(block._tick_id).toBe('tick-1');
      expect(block._lane).toBe('visible_scene_output');
    });

    test('returns null for null input', () => {
      expect(orchestrator._blockFromStreamEvent(null)).toBeNull();
    });

    test('returns null when block_payload is absent', () => {
      expect(orchestrator._blockFromStreamEvent({ event_id: 'x' })).toBeNull();
    });

    test('returns null when block_payload is not an object', () => {
      expect(orchestrator._blockFromStreamEvent({ block_payload: 'string' })).toBeNull();
    });

    test('defaults _lane to visible_scene_output when lane absent', () => {
      const event = {
        event_id: 'e1',
        tick_id: 't1',
        block_payload: { id: 'b1', block_type: 'narrator', text: 'Hi' },
      };
      const block = orchestrator._blockFromStreamEvent(event);
      expect(block._lane).toBe('visible_scene_output');
    });

    test('preserves all block_payload fields', () => {
      const payload = {
        id: 'b2',
        block_type: 'actor_line',
        text: 'Line',
        speaker_label: 'Véronique',
        actor_id: 'veronique',
        delivery: 'normal',
      };
      const event = { event_id: 'e2', tick_id: 't2', lane: 'visible_scene_output', block_payload: payload };
      const block = orchestrator._blockFromStreamEvent(event);
      expect(block.speaker_label).toBe('Véronique');
      expect(block.actor_id).toBe('veronique');
      expect(block.delivery).toBe('normal');
    });
  });

  describe('loadTurnFromEventStream()', () => {
    function makeStreamResponse(events, extraVso = {}) {
      return {
        visible_scene_output: {
          blocks: events.map((e) => e.block_payload),
          block_stream_events: events,
          ...extraVso,
        },
      };
    }

    function makeEvent(id, blockType = 'narrator', text = 'Text') {
      return {
        event_id: `evt-${id}`,
        tick_id: 'tick-1',
        lane: 'visible_scene_output',
        block_payload: { id, block_type: blockType, text },
      };
    }

    beforeEach(() => {
      // Ensure window flag is undefined (default off)
      delete window.WOS_PHASE2_BLOCK_STREAM_ENABLED;
    });

    afterEach(() => {
      delete window.WOS_PHASE2_BLOCK_STREAM_ENABLED;
    });

    test('falls back to loadTurn when feature gate is off', () => {
      const loadTurnSpy = jest.spyOn(orchestrator, 'loadTurn');
      const event = makeEvent('b1');
      const response = makeStreamResponse([event]);

      orchestrator.loadTurnFromEventStream(response);

      // loadTurn called with the original response (gate off → no synthetic vso)
      expect(loadTurnSpy).toHaveBeenCalledWith(response);
    });

    test('falls back to loadTurn when block_stream_events absent', () => {
      window.WOS_PHASE2_BLOCK_STREAM_ENABLED = true;
      const loadTurnSpy = jest.spyOn(orchestrator, 'loadTurn');
      const response = { visible_scene_output: { blocks: [{ id: 'b1', block_type: 'narrator', text: 'Hi' }] } };

      orchestrator.loadTurnFromEventStream(response);

      expect(loadTurnSpy).toHaveBeenCalledWith(response);
    });

    test('falls back to loadTurn when stream events have no valid block_payload', () => {
      window.WOS_PHASE2_BLOCK_STREAM_ENABLED = true;
      const loadTurnSpy = jest.spyOn(orchestrator, 'loadTurn');
      const response = {
        visible_scene_output: {
          blocks: [],
          block_stream_events: [{ event_id: 'e1' }], // no block_payload
        },
      };

      orchestrator.loadTurnFromEventStream(response);

      expect(loadTurnSpy).toHaveBeenCalledWith(response);
    });

    test('uses event stream when gate is on and events are valid', () => {
      window.WOS_PHASE2_BLOCK_STREAM_ENABLED = true;
      const loadTurnSpy = jest.spyOn(orchestrator, 'loadTurn');
      const event = makeEvent('b1');
      const response = makeStreamResponse([event]);

      orchestrator.loadTurnFromEventStream(response);

      // loadTurn called with synthetic response (not original)
      expect(loadTurnSpy).toHaveBeenCalledTimes(1);
      const callArg = loadTurnSpy.mock.calls[0][0];
      expect(callArg.visible_scene_output._source).toBe('phase2_event_stream');
      expect(callArg.visible_scene_output.typewriter_slice_start_index).toBe(0);
    });

    test('one event produces one rendered block', () => {
      window.WOS_PHASE2_BLOCK_STREAM_ENABLED = true;
      const event = makeEvent('b1');
      const response = makeStreamResponse([event]);

      orchestrator.loadTurnFromEventStream(response);

      expect(orchestrator.blocks).toHaveLength(1);
      expect(orchestrator.blocks[0].id).toBe('b1');
    });

    test('two events produce two blocks in order', () => {
      window.WOS_PHASE2_BLOCK_STREAM_ENABLED = true;
      const events = [makeEvent('b1', 'narrator', 'First'), makeEvent('b2', 'actor_line', 'Second')];
      const response = makeStreamResponse(events);

      orchestrator.loadTurnFromEventStream(response);

      expect(orchestrator.blocks).toHaveLength(2);
      expect(orchestrator.blocks[0].id).toBe('b1');
      expect(orchestrator.blocks[1].id).toBe('b2');
    });

    test('event-derived blocks carry trace fields', () => {
      window.WOS_PHASE2_BLOCK_STREAM_ENABLED = true;
      const event = makeEvent('b1');
      const response = makeStreamResponse([event]);

      orchestrator.loadTurnFromEventStream(response);

      expect(orchestrator.blocks[0]._stream_event_id).toBe('evt-b1');
      expect(orchestrator.blocks[0]._tick_id).toBe('tick-1');
    });

    test('synthetic vso preserves other vso fields', () => {
      window.WOS_PHASE2_BLOCK_STREAM_ENABLED = true;
      const loadTurnSpy = jest.spyOn(orchestrator, 'loadTurn');
      const event = makeEvent('b1');
      const response = makeStreamResponse([event], { contract: 'visible_scene_output.v1', extra_key: 'preserved' });

      orchestrator.loadTurnFromEventStream(response);

      const callArg = loadTurnSpy.mock.calls[0][0];
      expect(callArg.visible_scene_output.contract).toBe('visible_scene_output.v1');
      expect(callArg.visible_scene_output.extra_key).toBe('preserved');
    });

    test('typewriter starts delivery for the first event-derived block', () => {
      window.WOS_PHASE2_BLOCK_STREAM_ENABLED = true;
      const event = makeEvent('b1');
      const response = makeStreamResponse([event]);

      orchestrator.loadTurnFromEventStream(response);

      expect(mockTypewriter.startDelivery).toHaveBeenCalledWith(
        expect.objectContaining({ id: 'b1' }),
      );
    });

    test('original response is not mutated', () => {
      window.WOS_PHASE2_BLOCK_STREAM_ENABLED = true;
      const event = makeEvent('b1');
      const response = makeStreamResponse([event]);
      const originalBlocks = response.visible_scene_output.blocks.slice();

      orchestrator.loadTurnFromEventStream(response);

      expect(response.visible_scene_output.blocks).toEqual(originalBlocks);
      expect(response.visible_scene_output._source).toBeUndefined();
    });

    test('empty block_stream_events array falls back to loadTurn', () => {
      window.WOS_PHASE2_BLOCK_STREAM_ENABLED = true;
      const loadTurnSpy = jest.spyOn(orchestrator, 'loadTurn');
      const response = {
        visible_scene_output: {
          blocks: [{ id: 'b1', block_type: 'narrator', text: 'Hi' }],
          block_stream_events: [],
        },
      };

      orchestrator.loadTurnFromEventStream(response);

      expect(loadTurnSpy).toHaveBeenCalledWith(response);
    });
  });

  // ── Phase 2 Stage C: Primary Event Stream ────────────────────────────────

  describe('loadTurnFromEventStream() — Stage C primary', () => {
    function makeEvent(id, blockType = 'narrator', text = 'Text') {
      return {
        event_id: `evt-${id}`,
        tick_id: 'tick-1',
        lane: 'visible_scene_output',
        block_payload: { id, block_type: blockType, text },
      };
    }

    function makeStageCResponse(events, { canBePrimary = true, parityStatus = 'aligned', hasBundle = true } = {}) {
      return {
        visible_scene_output: {
          blocks: hasBundle ? events.map((e) => e.block_payload) : [],
          block_stream_events: events,
        },
        diagnostics: {
          phase2_event_stream_readiness: {
            can_be_primary_candidate: canBePrimary,
            parity_status: parityStatus,
            bundle_fallback_available: hasBundle,
            event_stream_present: events.length > 0,
          },
        },
      };
    }

    beforeEach(() => {
      delete window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED;
      delete window.WOS_PHASE2_BLOCK_STREAM_ENABLED;
    });

    afterEach(() => {
      delete window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED;
      delete window.WOS_PHASE2_BLOCK_STREAM_ENABLED;
    });

    test('Stage C disabled — uses bundle path', () => {
      const loadTurnSpy = jest.spyOn(orchestrator, 'loadTurn');
      const event = makeEvent('b1');
      const response = makeStageCResponse([event]);

      orchestrator.loadTurnFromEventStream(response);

      expect(loadTurnSpy).toHaveBeenCalledWith(response);
    });

    test('Stage C enabled + readiness candidate + valid events → uses event stream', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const loadTurnSpy = jest.spyOn(orchestrator, 'loadTurn');
      const event = makeEvent('b1');
      const response = makeStageCResponse([event], { canBePrimary: true });

      orchestrator.loadTurnFromEventStream(response);

      expect(loadTurnSpy).toHaveBeenCalledTimes(1);
      const callArg = loadTurnSpy.mock.calls[0][0];
      expect(callArg.visible_scene_output._source).toBe('phase2_primary_event_stream');
    });

    test('Stage C enabled + readiness candidate → blocks carry trace fields', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const event = makeEvent('b1');
      const response = makeStageCResponse([event], { canBePrimary: true });

      orchestrator.loadTurnFromEventStream(response);

      expect(orchestrator.blocks[0]._stream_event_id).toBe('evt-b1');
    });

    test('Stage C: one event renders one block', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const event = makeEvent('b1');
      const response = makeStageCResponse([event], { canBePrimary: true });

      orchestrator.loadTurnFromEventStream(response);

      expect(orchestrator.blocks).toHaveLength(1);
      expect(orchestrator.blocks[0].id).toBe('b1');
    });

    test('Stage C: two events produce two blocks in order', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const events = [makeEvent('b1', 'narrator', 'First'), makeEvent('b2', 'actor_line', 'Second')];
      const response = makeStageCResponse(events, { canBePrimary: true });

      orchestrator.loadTurnFromEventStream(response);

      expect(orchestrator.blocks).toHaveLength(2);
      expect(orchestrator.blocks[0].id).toBe('b1');
      expect(orchestrator.blocks[1].id).toBe('b2');
    });

    test('Stage C fallback: not candidate → falls back to bundle', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const loadTurnSpy = jest.spyOn(orchestrator, 'loadTurn');
      const event = makeEvent('b1');
      const response = makeStageCResponse([event], { canBePrimary: false, parityStatus: 'count_mismatch' });

      orchestrator.loadTurnFromEventStream(response);

      expect(loadTurnSpy).toHaveBeenCalledWith(response);
    });

    test('Stage C fallback: missing events → falls back', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const loadTurnSpy = jest.spyOn(orchestrator, 'loadTurn');
      const response = makeStageCResponse([], { canBePrimary: true });

      orchestrator.loadTurnFromEventStream(response);

      expect(loadTurnSpy).toHaveBeenCalledWith(response);
    });

    test('Stage C fallback: absent readiness diagnostics → falls back', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const loadTurnSpy = jest.spyOn(orchestrator, 'loadTurn');
      const event = makeEvent('b1');
      // No diagnostics field in response
      const response = {
        visible_scene_output: {
          blocks: [event.block_payload],
          block_stream_events: [event],
        },
      };

      orchestrator.loadTurnFromEventStream(response);

      expect(loadTurnSpy).toHaveBeenCalledWith(response);
    });

    test('Stage C: _lastPrimarySelection records primary used', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const event = makeEvent('b1');
      const response = makeStageCResponse([event], { canBePrimary: true, parityStatus: 'aligned' });

      orchestrator.loadTurnFromEventStream(response);

      const sel = orchestrator._lastPrimarySelection;
      expect(sel.event_stream_primary_attempted).toBe(true);
      expect(sel.event_stream_primary_used).toBe(true);
      expect(sel.event_stream_fallback_used).toBe(false);
      expect(sel.event_stream_fallback_reason).toBeNull();
      expect(sel.parity_status).toBe('aligned');
    });

    test('Stage C fallback: _lastPrimarySelection records fallback reason', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const event = makeEvent('b1');
      const response = makeStageCResponse([event], { canBePrimary: false, parityStatus: 'count_mismatch' });

      orchestrator.loadTurnFromEventStream(response);

      const sel = orchestrator._lastPrimarySelection;
      expect(sel.event_stream_primary_attempted).toBe(true);
      expect(sel.event_stream_primary_used).toBe(false);
      expect(sel.event_stream_fallback_used).toBe(true);
      expect(sel.event_stream_fallback_reason).toBe('readiness_not_candidate');
    });

    test('Stage C: fallback reason event_stream_invalid_or_missing when events absent', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const response = makeStageCResponse([], { canBePrimary: true });

      orchestrator.loadTurnFromEventStream(response);

      expect(orchestrator._lastPrimarySelection.event_stream_fallback_reason)
        .toBe('event_stream_invalid_or_missing');
    });

    test('Stage C: getState includes last_primary_selection', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const event = makeEvent('b1');
      const response = makeStageCResponse([event], { canBePrimary: true });

      orchestrator.loadTurnFromEventStream(response);

      const state = orchestrator.getState();
      expect(state.last_primary_selection).toBeDefined();
      expect(state.last_primary_selection.event_stream_primary_used).toBe(true);
    });

    test('Stage C disabled and Stage B disabled → both absent → loadTurn called directly', () => {
      const loadTurnSpy = jest.spyOn(orchestrator, 'loadTurn');
      const event = makeEvent('b1');
      const response = makeStageCResponse([event]);

      orchestrator.loadTurnFromEventStream(response);

      // No primary or Stage B flag — direct bundle path
      expect(loadTurnSpy).toHaveBeenCalledWith(response);
      expect(orchestrator._lastPrimarySelection).toBeNull();
    });

    test('Stage B still works when only Stage B flag set (no Stage C flag)', () => {
      window.WOS_PHASE2_BLOCK_STREAM_ENABLED = true;
      const loadTurnSpy = jest.spyOn(orchestrator, 'loadTurn');
      const event = makeEvent('b1');
      const response = {
        visible_scene_output: {
          blocks: [event.block_payload],
          block_stream_events: [event],
        },
      };

      orchestrator.loadTurnFromEventStream(response);

      const callArg = loadTurnSpy.mock.calls[0][0];
      expect(callArg.visible_scene_output._source).toBe('phase2_event_stream');
    });

    test('aligned stream primary output equivalent to bundle content', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const payload = { id: 'b1', block_type: 'narrator', text: 'Hello world.' };
      const event = { event_id: 'e1', tick_id: 't1', lane: 'visible_scene_output', block_payload: payload };
      const response = makeStageCResponse([event], { canBePrimary: true });

      orchestrator.loadTurnFromEventStream(response);

      // Block text matches original payload
      expect(orchestrator.blocks[0].id).toBe('b1');
      expect(orchestrator.blocks[0].text).toBe('Hello world.');
      expect(orchestrator.blocks[0].block_type).toBe('narrator');
    });

    test('original response not mutated by Stage C path', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const event = makeEvent('b1');
      const response = makeStageCResponse([event], { canBePrimary: true });
      const originalSource = response.visible_scene_output._source;

      orchestrator.loadTurnFromEventStream(response);

      expect(response.visible_scene_output._source).toBe(originalSource);
    });

    test('no Pi/Π runtime keys in selection diagnostics', () => {
      window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED = true;
      const event = makeEvent('b1');
      const response = makeStageCResponse([event], { canBePrimary: true });

      orchestrator.loadTurnFromEventStream(response);

      const selStr = JSON.stringify(orchestrator._lastPrimarySelection);
      expect(selStr).not.toMatch(/\bΠ\d+\b|\bPi\d+\b/);
    });
  });

  // ── Phase 2 WS Session Loop ────────────────────────────────────────────────

  describe('Phase 2 WS Session Loop', () => {
    function makeEvent(id, blockType = 'narrator', text = 'Hello') {
      return {
        event_id: `evt-${id}`,
        tick_id: 'tick-1',
        block_type: blockType,
        lane: 'visible_scene_output',
        block_payload: { id, block_type: blockType, text },
      };
    }

    beforeEach(() => {
      delete window.WOS_PHASE2_WS_SESSION_LOOP_ENABLED;
    });
    afterEach(() => {
      delete window.WOS_PHASE2_WS_SESSION_LOOP_ENABLED;
      try { orchestrator.disconnectStream(); } catch (_e) { /* ignore */ }
    });

    test('default getState exposes WS diagnostics fields with safe defaults', () => {
      const state = orchestrator.getState();
      expect(state).toEqual(
        expect.objectContaining({
          ws_session_loop_supported: false,
          live_interruption_supported: false,
          ws_connected: false,
          active_block_id: null,
          last_player_cut_in_event: null,
          cut_in_count: 0,
          stream_fallback_reason: null,
          proof_level: 'unknown',
          ws_queued_input_count: 0,
        }),
      );
    });

    test('connectStream — flag disabled → returns false, records fallback reason', () => {
      const onFallback = jest.fn();
      const ok = orchestrator.connectStream({ url: 'ws://x/', onFallback });
      expect(ok).toBe(false);
      expect(onFallback).toHaveBeenCalledWith('flag_disabled');
      expect(orchestrator.getState().stream_fallback_reason).toBe('flag_disabled');
    });

    test('connectStream — missing URL → returns false with fallback reason', () => {
      window.WOS_PHASE2_WS_SESSION_LOOP_ENABLED = true;
      const onFallback = jest.fn();
      const ok = orchestrator.connectStream({ url: '', onFallback });
      expect(ok).toBe(false);
      expect(onFallback).toHaveBeenCalledWith('missing_url');
      expect(orchestrator.getState().stream_fallback_reason).toBe('missing_url');
    });

    test('connectStream — WebSocket constructor throws → fallback reason recorded', () => {
      window.WOS_PHASE2_WS_SESSION_LOOP_ENABLED = true;
      const onFallback = jest.fn();
      const originalWS = global.WebSocket;
      global.WebSocket = function () { throw new Error('blocked'); };
      try {
        const ok = orchestrator.connectStream({ url: 'ws://x/', onFallback });
        expect(ok).toBe(false);
        expect(onFallback).toHaveBeenCalledWith('connect_threw');
      } finally {
        global.WebSocket = originalWS;
      }
    });

    test('_handleWsMessage stream_started flips support flag', () => {
      orchestrator._handleWsMessage({ kind: 'stream_started', session_id: 'sess-1' });
      const s = orchestrator.getState();
      expect(s.ws_session_loop_supported).toBe(true);
      expect(s.proof_level).toBe('live_loop_active');
    });

    test('_handleWsMessage block_started → renders block and sets active_block_id + live flag', () => {
      orchestrator._handleWsMessage({
        kind: 'block_started',
        event_id: 'evt-b1',
        block_stream_event: makeEvent('b1', 'narrator', 'First'),
      });
      const s = orchestrator.getState();
      expect(s.active_block_id).toBe('evt-b1');
      expect(s.live_interruption_supported).toBe(true);
      // appendNarratorBlock pushed onto blocks
      expect(orchestrator.blocks).toHaveLength(1);
      expect(orchestrator.blocks[0].id).toBe('b1');
    });

    test('_handleWsMessage block_completed → clears active flags', () => {
      orchestrator._handleWsMessage({
        kind: 'block_started',
        event_id: 'evt-b1',
        block_stream_event: makeEvent('b1'),
      });
      orchestrator._handleWsMessage({ kind: 'block_completed', event_id: 'evt-b1' });
      const s = orchestrator.getState();
      expect(s.active_block_id).toBe(null);
      expect(s.live_interruption_supported).toBe(false);
    });

    test('_handleWsMessage block_cut em_dash → cut_in_count increments + cut event captured', () => {
      orchestrator._handleWsMessage({
        kind: 'block_started',
        event_id: 'evt-b1',
        block_stream_event: makeEvent('b1', 'actor_line', 'Je suis—'),
      });
      const cutEvent = {
        schema_version: 'player_cut_in_event.v1',
        cut_in_id: 'cut-1',
        tick_id: 'tick-1',
        interrupted_block_id: 'evt-b1',
        interrupted_block_type: 'actor_line',
        cut_kind: 'em_dash',
        player_input_payload: { text: 'Stop!' },
      };
      orchestrator._handleWsMessage({
        kind: 'block_cut',
        cut_kind: 'em_dash',
        event_id: 'evt-b1',
        player_cut_in_event: cutEvent,
        drop_remaining_blocks: true,
        flush_active_block: false,
      });
      const s = orchestrator.getState();
      expect(s.cut_in_count).toBe(1);
      expect(s.last_player_cut_in_event).toEqual(cutEvent);
      expect(s.active_block_id).toBe(null);
    });

    test('_handleWsMessage block_cut skip_to_end → calls revealAll', () => {
      const revealSpy = jest.spyOn(orchestrator, 'revealAll').mockImplementation(() => {});
      orchestrator._handleWsMessage({
        kind: 'block_cut',
        cut_kind: 'skip_to_end',
        player_cut_in_event: { cut_kind: 'skip_to_end' },
      });
      expect(revealSpy).toHaveBeenCalledTimes(1);
    });

    test('_handleWsMessage stream_error → sets stream_fallback_reason', () => {
      orchestrator._handleWsMessage({ kind: 'stream_error', reason: 'turn_execution_failed' });
      expect(orchestrator.getState().stream_fallback_reason).toBe('turn_execution_failed');
    });

    test('sendCutIn queues input when socket not open and does not lose it', () => {
      const result = orchestrator.sendCutIn('Hello');
      expect(result).toBe(false);
      const drained = orchestrator.drainQueuedPlayerInputs();
      expect(drained).toHaveLength(1);
      expect(drained[0].player_input).toBe('Hello');
      // After drain, the queue is empty.
      expect(orchestrator.getState().ws_queued_input_count).toBe(0);
    });

    test('wsStartTurn rejects when socket not open', () => {
      const ok = orchestrator.wsStartTurn('go');
      expect(ok).toBe(false);
    });

    test('no Pi/Π runtime keys in WS diagnostics', () => {
      orchestrator._handleWsMessage({ kind: 'stream_started', session_id: 's' });
      orchestrator._handleWsMessage({
        kind: 'block_started',
        event_id: 'evt-b1',
        block_stream_event: makeEvent('b1'),
      });
      const stateStr = JSON.stringify(orchestrator.getState());
      expect(stateStr).not.toMatch(/\bΠ\d+\b|\bPi\d+\b/);
    });

    test('cut-in semantics by block type: actor_line → em_dash drops queue, skip_to_end flushes', () => {
      // Pure renderer-side: verify the orchestrator handles each cut_kind without
      // mishandling the active block state.
      orchestrator._handleWsMessage({ kind: 'stream_started', session_id: 's' });
      orchestrator._handleWsMessage({
        kind: 'block_started', event_id: 'evt-a', block_stream_event: makeEvent('a', 'actor_line', 'hi'),
      });
      orchestrator._handleWsMessage({
        kind: 'block_cut',
        cut_kind: 'em_dash',
        player_cut_in_event: { cut_kind: 'em_dash' },
        drop_remaining_blocks: true,
        flush_active_block: false,
      });
      let s = orchestrator.getState();
      expect(s.cut_in_count).toBe(1);
      expect(s.active_block_id).toBe(null);

      // Second cycle: narrator + skip_to_end
      const revealSpy = jest.spyOn(orchestrator, 'revealAll').mockImplementation(() => {});
      orchestrator._handleWsMessage({
        kind: 'block_started', event_id: 'evt-n', block_stream_event: makeEvent('n', 'narrator', 'creak'),
      });
      orchestrator._handleWsMessage({
        kind: 'block_cut',
        cut_kind: 'skip_to_end',
        player_cut_in_event: { cut_kind: 'skip_to_end' },
        drop_remaining_blocks: true,
        flush_active_block: true,
      });
      s = orchestrator.getState();
      expect(s.cut_in_count).toBe(2);
      expect(revealSpy).toHaveBeenCalledTimes(1);
    });

    test('no_active_block cut-in does not affect renderer state', () => {
      const revealSpy = jest.spyOn(orchestrator, 'revealAll').mockImplementation(() => {});
      orchestrator._handleWsMessage({
        kind: 'block_cut',
        cut_kind: 'no_active_block',
        player_cut_in_event: { cut_kind: 'no_active_block' },
        drop_remaining_blocks: false,
        flush_active_block: false,
      });
      expect(revealSpy).not.toHaveBeenCalled();
      expect(orchestrator.getState().cut_in_count).toBe(1);
    });

    // ── Phase 2 Stage E — autonomous Director tick reception ──────────────

    function makeAutonomousEvent(id, actorId, text = 'autonomous line', tickId = 'tick-auto-1') {
      return {
        schema_version: 'block_stream_event.v1',
        event_id: 'evt-' + id,
        tick_id: tickId,
        block_type: 'actor_line',
        cut_in_state: 'uninterrupted',
        lane: 'visible_scene_output',
        source: actorId,
        block_payload: {
          id,
          block_type: 'actor_line',
          actor_id: actorId,
          text,
          originator: 'autonomous_tick',
          autonomous_tick_id: tickId,
        },
      };
    }

    test('default getState exposes Stage E autonomous-tick counters at zero', () => {
      const state = orchestrator.getState();
      expect(state).toEqual(
        expect.objectContaining({
          autonomous_tick_evaluated_count: 0,
          autonomous_tick_block_received_count: 0,
          autonomous_tick_silence_count: 0,
          autonomous_tick_cut_in_interrupted_count: 0,
          last_autonomous_tick_summary: null,
          active_block_is_autonomous: false,
        }),
      );
    });

    test('autonomous_tick_evaluated message records summary and increments counter', () => {
      const summary = {
        tick_id: 'tick-1',
        tick_trigger_kind: 'motivation_threshold_crossed',
        chosen_actor_id: 'npc_a',
        chosen_action_kind: 'speak',
        block_emitted: true,
        motivation_scores: { npc_a: 0.8 },
        cooldown_state: { cooldown_active: false, min_tick_interval_ms: 1500 },
        silence_reason: null,
      };
      orchestrator._handleWsMessage({ kind: 'autonomous_tick_evaluated', summary });
      const s = orchestrator.getState();
      expect(s.autonomous_tick_evaluated_count).toBe(1);
      expect(s.last_autonomous_tick_summary).toEqual(summary);
      expect(s.autonomous_tick_silence_count).toBe(0);
    });

    test('autonomous_tick_evaluated with silence increments silence counter', () => {
      const summary = {
        tick_id: 'tick-2',
        chosen_actor_id: null,
        block_emitted: false,
        silence_reason: 'no_npc_above_motivation_threshold',
        motivation_scores: {},
        cooldown_state: { cooldown_active: false, min_tick_interval_ms: 1500 },
      };
      orchestrator._handleWsMessage({ kind: 'autonomous_tick_evaluated', summary });
      const s = orchestrator.getState();
      expect(s.autonomous_tick_evaluated_count).toBe(1);
      expect(s.autonomous_tick_silence_count).toBe(1);
      expect(s.autonomous_tick_block_received_count).toBe(0);
    });

    test('autonomous block_started is recognised via originator + counter increments', () => {
      const event = makeAutonomousEvent('b-auto', 'npc_a');
      orchestrator._handleWsMessage({
        kind: 'block_started',
        event_id: event.event_id,
        block_stream_event: event,
      });
      const s = orchestrator.getState();
      expect(s.active_block_is_autonomous).toBe(true);
      expect(s.autonomous_tick_block_received_count).toBe(1);
    });

    test('non-autonomous block_started leaves Stage E counters untouched', () => {
      orchestrator._handleWsMessage({
        kind: 'block_started',
        event_id: 'evt-user',
        block_stream_event: makeEvent('user-block', 'narrator', 'Player turn'),
      });
      const s = orchestrator.getState();
      expect(s.active_block_is_autonomous).toBe(false);
      expect(s.autonomous_tick_block_received_count).toBe(0);
    });

    test('cut-in during autonomous actor_line increments cut_in_interrupted counter', () => {
      const event = makeAutonomousEvent('b-auto', 'npc_a');
      orchestrator._handleWsMessage({
        kind: 'block_started',
        event_id: event.event_id,
        block_stream_event: event,
      });
      orchestrator._handleWsMessage({
        kind: 'block_cut',
        cut_kind: 'em_dash',
        event_id: event.event_id,
        block_type: 'actor_line',
        player_cut_in_event: {
          schema_version: 'player_cut_in_event.v1',
          cut_kind: 'em_dash',
          interrupted_block_id: event.event_id,
          interrupted_block_type: 'actor_line',
          player_input_payload: { text: 'Wait!' },
        },
        drop_remaining_blocks: true,
        flush_active_block: false,
      });
      const s = orchestrator.getState();
      expect(s.autonomous_tick_cut_in_interrupted_count).toBe(1);
      expect(s.cut_in_count).toBe(1);
      expect(s.active_block_is_autonomous).toBe(false);
    });

    test('cut-in during non-autonomous block does NOT touch autonomous counter', () => {
      orchestrator._handleWsMessage({
        kind: 'block_started',
        event_id: 'evt-user',
        block_stream_event: makeEvent('user', 'actor_line', 'human says'),
      });
      orchestrator._handleWsMessage({
        kind: 'block_cut',
        cut_kind: 'em_dash',
        player_cut_in_event: { cut_kind: 'em_dash' },
      });
      const s = orchestrator.getState();
      expect(s.cut_in_count).toBe(1);
      expect(s.autonomous_tick_cut_in_interrupted_count).toBe(0);
    });

    test('autonomous block recognised even without originator if tick_id matches last summary', () => {
      orchestrator._handleWsMessage({
        kind: 'autonomous_tick_evaluated',
        summary: {
          tick_id: 'tick-shared',
          chosen_actor_id: 'npc_b',
          block_emitted: true,
          motivation_scores: { npc_b: 0.9 },
          cooldown_state: { cooldown_active: false, min_tick_interval_ms: 1500 },
        },
      });
      // A block whose payload lacks originator but shares tick_id with the
      // evaluated summary still counts as autonomous (defensive fallback).
      const event = {
        schema_version: 'block_stream_event.v1',
        event_id: 'evt-x',
        tick_id: 'tick-shared',
        block_type: 'actor_line',
        cut_in_state: 'uninterrupted',
        lane: 'visible_scene_output',
        source: 'npc_b',
        block_payload: {
          id: 'x', block_type: 'actor_line', actor_id: 'npc_b', text: 'shared tick',
        },
      };
      orchestrator._handleWsMessage({
        kind: 'block_started', event_id: 'evt-x', block_stream_event: event,
      });
      expect(orchestrator.getState().autonomous_tick_block_received_count).toBe(1);
    });

    test('no Pi/Π keys in Stage E diagnostic state', () => {
      orchestrator._handleWsMessage({
        kind: 'autonomous_tick_evaluated',
        summary: {
          tick_id: 't', chosen_actor_id: 'npc_a', block_emitted: false,
          silence_reason: 'no_npc_above_motivation_threshold',
          motivation_scores: { npc_a: 0.3 },
          cooldown_state: { cooldown_active: false, min_tick_interval_ms: 1500 },
        },
      });
      const stateStr = JSON.stringify(orchestrator.getState());
      expect(stateStr).not.toMatch(/\bΠ\d+\b|\bPi\d+\b/);
    });
  });
});
