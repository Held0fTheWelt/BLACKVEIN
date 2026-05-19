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
});
