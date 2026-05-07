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
      expect(mockRenderer.render).toHaveBeenCalledTimes(2);
      expect(mockTypewriter.startDelivery).toHaveBeenCalledTimes(1);
      expect(mockTypewriter.startDelivery).toHaveBeenCalledWith(
        expect.objectContaining({ id: 'block-2', text: 'Second' }),
      );
    });

    test('with typewriter_slice_start_index 0, keeps only the last block active', () => {
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

      expect(mockTypewriter.startDelivery).toHaveBeenCalledTimes(1);
      expect(mockTypewriter.startDelivery).toHaveBeenCalledWith(
        expect.objectContaining({ id: 'block-2' }),
      );
      const el = container.querySelector('[data-block-id="block-1"]');
      expect(el.textContent).toBe('First');
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
    test('should skip current block and increment index', () => {
      mockTypewriter.getQueueState.mockReturnValue({ current_block_id: 'block-2' });
      orchestrator.blocks = [{ id: 'block-1', text: 'First' }, { id: 'block-2', text: 'Second' }];

      orchestrator.skipCurrentBlock();

      expect(mockTypewriter.skipBlock).toHaveBeenCalledWith('block-2');
      expect(orchestrator.currentBlockIndex).toBe(2);
    });

    test('should handle multiple skips in sequence', () => {
      orchestrator.blocks = [
        { id: 'block-1', text: 'First' },
        { id: 'block-2', text: 'Second' },
        { id: 'block-3', text: 'Third' },
      ];

      mockTypewriter.getQueueState.mockReturnValue({ current_block_id: 'block-1' });
      orchestrator.skipCurrentBlock();
      expect(orchestrator.currentBlockIndex).toBe(3);

      mockTypewriter.getQueueState.mockReturnValue({ current_block_id: 'block-2' });
      orchestrator.skipCurrentBlock();
      expect(orchestrator.currentBlockIndex).toBe(3);

      mockTypewriter.getQueueState.mockReturnValue({ current_block_id: 'block-3' });
      orchestrator.skipCurrentBlock();
      expect(orchestrator.currentBlockIndex).toBe(3);
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
          blocks: [
            { id: 'b1', block_type: 'narrator', text: 'First' },
            { id: 'b2', block_type: 'actor_line', text: 'Second' },
          ],
        },
      };

      orch.loadTurn(response);

      expect(realContainer.children.length).toBe(2);
      expect(realContainer.children[0].getAttribute('data-block-id')).toBe('b1');
      expect(realContainer.children[1].getAttribute('data-block-id')).toBe('b2');

      document.body.removeChild(realContainer);
    });
  });

  describe('diagnostics block filtering', () => {
    test('should not enqueue diagnostics blocks for typewriter', () => {
      orchestrator.loadTurn({
        visible_scene_output: {
          blocks: [
            { id: 'b1', block_type: 'narrator_scene', text: 'Scene' },
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
});
